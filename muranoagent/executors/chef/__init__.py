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

import bunch
import json
import os
import subprocess

import muranoagent.exceptions
from muranoagent import executors
from muranoagent.openstack.common import log as logging


LOG = logging.getLogger(__name__)


@executors.executor('Chef')
class ChefExecutor(object):
    def __init__(self, name):
        self._name = name

    def load(self, path, options):
        """It loads the path and options from template into
        the chef executor.

           :param path: The path
           :param options: execution plan options.
        """
        self._path = path
        self._capture_stdout = options.get('captureStdout', True)
        self._capture_stderr = options.get('captureStderr', True)
        self._verify_exitcode = options.get('verifyExitcode', True)

    def run(self, function, recipe_attributes=None, input=None):
        """It runs the chef executor.

           :param function: The function
           :param recipe_attributes: recipe attributes
           :param input:
        """
        if not self._valid_name(self._name):
            msg = ("Cookbook recipe name format {0} is not valid".
                   format(self._name))
            LOG.debug(msg)
            raise muranoagent.exceptions.CustomException(
                0,
                message=msg,
                additional_data=None)

        self.cookbook_name = self._name[0:self._name.rfind('::')]
        self.cookbook_recipe = self._name[self._name.rfind('::') + 2:]

        try:
            self._configure_chef()
            self._generate_manifest(self.cookbook_name,
                                    self.cookbook_recipe, recipe_attributes)
        except Exception as e:
            result = {
                'exitCode': 2,
                'stdout': None,
                'stderr': e.strerror
            }
            raise muranoagent.exceptions.CustomException(
                0,
                message='Cookbook {0} returned error code {1}: {2}'.format(
                    self.cookbook_name, self.cookbook_recipe, e.strerror,
                ), additional_data=result)

        stdout = subprocess.PIPE if self._capture_stdout else None
        stderr = subprocess.PIPE if self._capture_stderr else None
        solo_file = os.path.join(self._path, "files", "solo.rb")
        process = subprocess.Popen(
            'chef-solo -j node.json -c ' + solo_file,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            cwd=os.getcwd(),
            shell=True)
        stdout, stderr = process.communicate(input)
        retcode = process.poll()

        if stdout is not None:
            stdout = stdout.decode('utf-8')
            LOG.debug(u"'{0}' execution stdout: "
                      u"'{1}'".format(self.cookbook_name, stdout))
        if stderr is not None:
            for line in stdout.splitlines():
                if 'ERROR' in line:
                    stderr += line + "\n"
            LOG.debug(u"'{0}' execution stderr: "
                      u"'{1}'".format(self.cookbook_name, stderr))

        LOG.debug('Script {0} execution finished \
            with retcode: {1} {2}'.format(self.cookbook_name, retcode, stderr))
        result = {
            'exitCode': retcode,
            'stdout': stdout.strip() if stdout else None,
            'stderr': stderr.strip() if stderr else None,
        }
        if self._verify_exitcode and retcode:
            raise muranoagent.exceptions.CustomException(
                0,
                message='Script {0} returned error code'.format(self._name),
                additional_data=result)

        return bunch.Bunch(result)

    def _valid_name(self, name):
        return '::' in self._name

    def _configure_chef(self):
        """It generates the chef files for configuration."""
        solo_file = os.path.join(self._path, 'files', 'solo.rb')
        if not os.path.exists(solo_file):
            path = os.path.abspath(os.path.join(self._path, "files"))
            if not os.path.isdir(path):
                os.makedirs(path)
            with open(solo_file, "w+") as f:
                f.write('cookbook_path \"' + path + '\"')

    def _generate_manifest(self, cookbook_name,
                           cookbook_recipe, recipe_attributes):
        """It generates the chef manifest."""
        node = self._create_manifest(cookbook_name, cookbook_recipe,
                                     recipe_attributes)
        with open("node.json", "w+") as f:
            f.write(node)

    def _create_manifest(self, cookbook_name, cookbook_recipe,
                         recipe_attributes):
        node = {}
        node["run_list"] = [u"recipe[{0}::{1}]".format(
            cookbook_name, cookbook_recipe)]

        if recipe_attributes:
            node[cookbook_name] = recipe_attributes.copy()

        return json.dumps(node)
