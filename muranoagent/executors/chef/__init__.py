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
from muranoagent.executors import chef_puppet_executor_base


LOG = logging.getLogger(__name__)


@executors.executor('Chef')
class ChefExecutor(chef_puppet_executor_base.ChefPuppetExecutorBase):

    def load(self, path, options):
        super(ChefExecutor, self).load(path, options)
        self._use_berkshelf = options.get('useBerkshelf', False)
        self._berksfile_path = options.get('berksfilePath', None)

    def run(self, function, recipe_attributes=None, input=None):
        """It runs the chef executor.

           :param function: The function
           :param recipe_attributes: recipe attributes
           :param input:
        """
        self._valid_module_name()

        cookbook_path = self._create_cookbook_path(self.module_name)

        try:
            self._configure_chef(cookbook_path)
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

        solo_file = os.path.join(self._path, "solo.rb")
        command = 'chef-solo -j node.json -c {0}'.format(solo_file)
        result = self._execute_command(command)
        return bunch.Bunch(result)

    def _create_cookbook_path(self, cookbook_name):
        """It defines a path where all required cookbooks are located."""
        path = os.path.abspath(self._path)

        if self._use_berkshelf:
            LOG.debug('Using Berkshelf')

            # Get Berksfile
            if self._berksfile_path is None:
                self._berksfile_path = cookbook_name + '/Berksfile'
            berksfile = os.path.join(path, self._berksfile_path)
            if not os.path.isfile(berksfile):
                msg = "Berskfile {0} not found".format(berksfile)
                LOG.debug(msg)
                raise muranoagent.exceptions.CustomException(
                    0,
                    message=msg,
                    additional_data=None)

            # Create cookbooks path
            cookbook_path = os.path.join(path, "berks-cookbooks")
            if not os.path.isdir(cookbook_path):
                os.makedirs(cookbook_path)

            # Vendor cookbook and its dependencies to cookbook_path
            command = 'berks vendor --berksfile={0} {1}'.format(
                berksfile,
                cookbook_path)
            result = self._execute_command(command)
            if result['exitCode'] != 0:
                raise muranoagent.exceptions.CustomException(
                    0,
                    message='Berks returned error code',
                    additional_data=result)

            return cookbook_path

        else:
            return path

    def _configure_chef(self, cookbook_path):
        """It generates the chef files for configuration."""
        solo_file = os.path.join(self._path, 'solo.rb')
        if not os.path.exists(solo_file):
            if not os.path.isdir(self._path):
                os.makedirs(self._path)
            with open(solo_file, "w+") as f:
                f.write('cookbook_path \"' + cookbook_path + '\"')

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
