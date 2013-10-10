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
from muranoagent.executors import executor
import muranoagent.exceptions
from bunch import Bunch


@executor('Application')
class ApplicationExecutor(object):
    def __init__(self, name):
        self._capture_stdout = False
        self._capture_stderr = False
        self._verify_exitcode = True
        self._name = name

    def load(self, path, options):
        self._path = path
        self._capture_stdout = options.get('captureStdout', False)
        self._capture_stderr = options.get('captureStderr', False)
        self._verify_exitcode = options.get('verifyExitcode', True)

    def run(self, function, commandline, input=None):
        dir_name = os.path.dirname(self._path)
        os.chdir(dir_name)
        app = '"{0}" {1}'.format(os.path.basename(self._path), commandline)

        if not sys.platform == 'win32':
            os.chmod(self._path, stat.S_IEXEC | stat.S_IREAD)
            app = './' + app

        stdout = subprocess.PIPE if self._capture_stdout else None
        stderr = subprocess.PIPE if self._capture_stderr else None

        process = subprocess.Popen(
            app,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            cwd=dir_name,
            shell=True)
        stdout, stderr = process.communicate(input)
        retcode = process.poll()

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

        return Bunch(result)
