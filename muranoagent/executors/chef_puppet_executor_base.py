# Copyright (c) 2015 Telefonica I+D
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

import json
import os
import subprocess

from oslo_log import log as logging

from muranoagent import bunch
import muranoagent.exceptions
from muranoagent import executors


LOG = logging.getLogger(__name__)


class ChefPuppetExecutorBase(object):
    def __init__(self, name):
        self._name = name

    def load(self, path, options):
        """Load the path and options from template into the executor.

           :param path: The path
           :param options: execution plan options.

        """
        self._path = path
        self._capture_stdout = options.get('captureStdout', True)
        self._capture_stderr = options.get('captureStderr', True)
        self._verify_exitcode = options.get('verifyExitcode', True)

    def _valid_module_name(self):
        if not self._valid_name(self._name):
            msg = ("Module recipe name format {0} is not valid".
                   format(self._name))
            LOG.debug(msg)
            raise muranoagent.exceptions.CustomException(
                0,
                message=msg,
                additional_data=None)

        self.module_name = self._name[0:self._name.rfind('::')]
        self.module_recipe = self._name[self._name.rfind('::') + 2:]

    def _valid_name(self, name):
        return '::' in name

    def _execute_command(self, command):
        stdout = subprocess.PIPE if self._capture_stdout else None
        stderr = subprocess.PIPE if self._capture_stderr else None
        process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            cwd=os.getcwd(),
            shell=True)
        stdout, stderr = process.communicate(input)
        retcode = process.poll()

        if stdout is not None:
            if not isinstance(stdout, str):
                stdout = stdout.decode('utf-8')
            LOG.debug(u"'{0}' execution stdout: "
                      u"'{1}'".format(self.module_name, stdout))
        if stderr is not None:
            for line in stdout.splitlines():
                if 'ERROR' in line:
                    stderr += line + "\n"
            LOG.debug(u"'{0}' execution stderr: "
                      u"'{1}'".format(self.module_name, stderr))

        LOG.debug('Script {0} execution finished \
            with retcode: {1} {2}'.format(self.module_name, retcode, stderr))
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

        return result
