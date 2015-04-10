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
from muranoagent.executors import chef_puppet_executor_base
from muranoagent.openstack.common import log as logging


LOG = logging.getLogger(__name__)


@executors.executor('Chef')
class ChefExecutor(chef_puppet_executor_base.ChefPuppetExecutorBase):

    def run(self, function, recipe_attributes=None, input=None):
        """It runs the chef executor.

           :param function: The function
           :param recipe_attributes: recipe attributes
           :param input:
        """
        self._valid_module_name()

        try:
            self._configure_chef()
            self._generate_manifest(self.module_name,
                                    self.module_recipe, recipe_attributes)
        except Exception as e:
            result = {
                'exitCode': 2,
                'stdout': None,
                'stderr': e.strerror
            }
            raise muranoagent.exceptions.CustomException(
                0,
                message='Cookbook {0} returned error code {1}: {2}'.format(
                    self.module_name, self.module_recipe, e.strerror,
                ), additional_data=result)

        solo_file = os.path.join(self._path, "files", "solo.rb")
        command = 'chef-solo -j node.json -c {0}'.format(solo_file)
        result = self._execute_command(command)
        return bunch.Bunch(result)

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
