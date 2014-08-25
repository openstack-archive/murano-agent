# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import os
import shutil

from muranoagent.common import config

CONF = config.CONF


class FilesManager(object):
    def __init__(self, execution_pan):
        self._fetched_files = {}
        self._files = execution_pan.get('Files') or {}

        self._cache_folder = os.path.join(
            CONF.storage, 'files', execution_pan.ID)
        if os.path.exists(self._cache_folder):
            self.clear()
        os.makedirs(self._cache_folder)

    def put_file(self, file_id, script):
        cache_path = self._fetch_file(file_id)

        script_folder = os.path.join(self._cache_folder, script)
        if not os.path.exists(script_folder):
            os.mkdir(script_folder)

        filedef = self._files[file_id]
        filename = filedef['Name']

        file_folder = os.path.join(script_folder, os.path.dirname(filename))
        if not os.path.exists(file_folder):
            os.makedirs(file_folder)

        script_path = os.path.join(script_folder, filename)

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
                out_file.write(base64.b64decode(filedef['Body']))

        self._fetched_files[file_id] = out_path
        return out_path

    def clear(self):
        os.chdir(os.path.dirname(self._cache_folder))
        shutil.rmtree(self._cache_folder, ignore_errors=True)
        shutil.rmtree(self._cache_folder, ignore_errors=True)
