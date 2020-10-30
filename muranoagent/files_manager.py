# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import git
import os
import re
import requests
import shutil
import subprocess

from oslo_log import log as logging
from oslo_utils import encodeutils
import urllib

from muranoagent.common import config
from muranoagent import util

CONF = config.CONF
LOG = logging.getLogger(__name__)


class FilesManager(object):
    def __init__(self, execution_plan):
        self._fetched_files = {}
        self._files = execution_plan.get('Files') or {}

        self._cache_folder = os.path.join(
            CONF.storage, 'files', execution_plan.ID)
        if os.path.exists(self._cache_folder):
            self.clear()
        os.makedirs(self._cache_folder, 0o700)

    def put_file(self, file_id, script):
        if type(file_id) is dict:
            file_name = list(file_id.keys())[0]
            file_def = file_id[file_name]
        else:
            file_def = self._files[file_id]
            file_name = file_def['Name']

        if file_def.get('Type') == 'Downloadable':
            cache_folder = self._download_url_file(file_def, file_id)
            return self._make_symlink(cache_folder, file_name, script)
        else:
            cache_path = self._fetch_file(file_id)
            return self._make_symlink(cache_path, file_name, script)

    def _make_symlink(self, cache_path, file_name, script):
        script_folder = os.path.join(self._cache_folder, script)
        if not os.path.isdir(script_folder):
            os.mkdir(script_folder)

        file_folder = os.path.join(script_folder,
                                   os.path.dirname(file_name))
        if not os.path.isdir(file_folder):
            os.makedirs(file_folder)

        if cache_path is not None:
            script_path = os.path.join(script_folder, file_name)
            if not os.path.lexists(script_path):
                os.symlink(cache_path, script_path)
            return script_path

    def _fetch_file(self, file_id):
        if file_id in self._fetched_files:
            return self._fetched_files[file_id]

        filedef = self._files[file_id]
        out_path = os.path.join(self._cache_folder, file_id)
        body_type = filedef.get('BodyType', 'Text')
        with open(out_path, 'w') as out_file:
            if body_type == 'Text':
                out_file.write(filedef['Body'])
            elif body_type == 'Base64':
                out_file.write(util.b64decode(filedef['Body']))

        self._fetched_files[file_id] = out_path
        return out_path

    def _download_url_file(self, file_def, file_id):
        """It download the file in the murano-agent.

        It can proceed from a git file or any other internal URL
           :param file_def: file description
           :param file_id: the ID file to download
           :param input:
        """
        folder = os.path.join(self._cache_folder, file_id)
        if os.path.isdir(folder):
            return folder

        if 'URL' not in file_def:
            raise ValueError("No valid URL in file {0}".
                             format(file_def))
        url_file = file_def['URL']

        if not self._url(url_file):
            raise ValueError("Provided URL is not valid {0}".
                             format(url_file))

        if not os.path.isdir(folder):
            os.makedirs(folder)

        try:
            if self._is_git_repository(url_file):
                git.Git().clone(url_file, folder)
            elif self._is_svn_repository(url_file):
                self._download_svn(url_file, folder)
            else:
                self._download_file(url_file, folder)
        except Exception as e:
            if self._is_git_repository(url_file):
                mns = ("Error to clone the git repository {0}: {1}".
                       format(url_file, e.message))
            else:
                mns = ("Error to download the file {0}: {1}".
                       format(url_file, e.message))
            LOG.warning(mns)
            raise ValueError(mns)
        return folder

    def clear(self):
        shutil.rmtree(self._cache_folder, ignore_errors=True)

    def _download_file(self, url, path):
        local_filename = url.split('/')[-1]
        r = requests.get(url, stream=True)
        with open(os.path.join(path, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
        return local_filename

    def _url(self, file):
        return (urllib.parse.urlsplit(file).scheme or
                urllib.parse.urlsplit(file).netloc)

    def _is_git_repository(self, url):
        return (url.startswith(("git://",
                               "git+http://", "git+https:/"))
                or url.endswith('.git'))

    def _is_svn_repository(self, url):
        http_regex = "https?://(.*)/svn/(.*)"
        http_matches = re.search(http_regex, url)
        svn_regex = "svn://(.*)"
        svn_matches = re.search(svn_regex, url)
        if http_matches is None and svn_matches is None:
            return False
        else:
            return True

    def _download_svn(self, url_file, folder):
        self._execute_command("svn checkout {0} --non-interactive "
                              "--trust-server-cert {1}".
                              format(url_file, folder))

    def _execute_command(self, command):

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=os.getcwd(),
            shell=True)
        stdout, stderr = process.communicate(input)
        retcode = process.poll()

        if stdout is not None:
            stdout = encodeutils.safe_decode('utf-8')
            LOG.debug(stdout)

        if stderr is not None:
            stderr = encodeutils.safe_decode('utf-8')
            LOG.error(stderr)

        if retcode != 0:
            raise ValueError(stderr)
