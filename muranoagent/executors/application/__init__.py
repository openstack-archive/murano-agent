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

import os
import stat
import subprocess
import sys

import bunch

import muranoagent.exceptions
from muranoagent import executors
from muranoagent.openstack.common import log as logging

LOG = logging.getLogger(__name__)


@executors.executor('Application')
class ApplicationExecutor(object):
    def __init__(self, name):
        self._name = name

    def load(self, path, options):
        self._path = path
        self._capture_stdout = options.get('captureStdout', True)
        self._capture_stderr = options.get('captureStderr', True)
        self._verify_exitcode = options.get('verifyExitcode', True)

    def run(self, function, commandline='', input=None):
        dir_name = os.path.dirname(self._path)
        os.chdir(dir_name)
        app = '"{0}" {1}'.format(os.path.basename(self._path), commandline)

        if not sys.platform == 'win32':
            os.chmod(self._path, stat.S_IEXEC | stat.S_IREAD)
            app = './' + app

        stdout = subprocess.PIPE if self._capture_stdout else None
        stderr = subprocess.PIPE if self._capture_stderr else None
        script_name = os.path.relpath(self._path)
        LOG.debug("Starting '{0}' script execution".format(script_name))

        process = subprocess.Popen(
            app,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            cwd=dir_name,
            shell=True)
        stdout, stderr = process.communicate(input)
        retcode = process.poll()
        LOG.debug("Script {0} execution finished "
                  "with retcode: {1}".format(script_name, retcode))
        if stdout is not None:
            stdout = stdout.decode('utf-8')
            LOG.debug(u"'{0}' execution stdout: "
                      u"'{1}'".format(script_name, stdout))
        if stderr is not None:
            stderr = stderr.decode('utf-8')
            LOG.debug(u"'{0}' execution stderr: "
                      u"'{1}'".format(script_name, stderr))
        result = {
            'exitCode': retcode,
            'stdout': stdout.strip() if stdout else None,
            'stderr': stderr.strip() if stderr else None
        }
        if self._verify_exitcode and retcode != 0:
            raise muranoagent.exceptions.CustomException(
                0,
                message='Script {0} returned error code'.format(self._name),
                additional_data=result)

        return bunch.Bunch(result)
