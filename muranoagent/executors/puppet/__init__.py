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
import os
import subprocess
import yaml

from muranoagent import bunch
import muranoagent.exceptions
from muranoagent import executors
from muranoagent.executors import chef_puppet_executor_base


@executors.executor('Puppet')
class PuppetExecutor(chef_puppet_executor_base.ChefPuppetExecutorBase):

    def run(self, function, recipe_attributes=None, input=None):
        """It runs the puppet executor.

           :param function: The function
           :param recipe_attributes: recipe attributes
           :param input:
        """
        self._valid_module_name()

        try:
            self._configure_puppet()
            self._generate_files(self.module_name, self.module_recipe,
                                 recipe_attributes)
        except Exception as e:
            result = {
                'exitCode': 2,
                'stdout': None,
                'stderr': e.strerror
            }
            raise muranoagent.exceptions.CustomException(
                0,
                message='Module %s returned error code %s: %s' %
                        (self.module_name, self.module_recipe, e.strerror),
                additional_data=result)

        command = 'puppet apply --hiera_config=hiera.yaml --modulepath ' \
                  '{0} manifest.pp'.format(self._path)
        result = self._execute_command(command)
        return bunch.Bunch(result)

    def _configure_puppet(self):

        if os.path.exists('hiera.yaml'):
            return

        data = dict(
            backends='yaml',
            logger='console',
            hierarchy='%{env}',
            yaml=dict(datadir='/etc/puppet/hieradata')
        )

        self._write_yaml_file('hiera.yaml', data)

    def _generate_files(self, module, module_recipe, recipe_attributes):
        manifest = self._create_manifest(module, module_recipe)
        with open("manifest.pp", "w+") as f:
            f.write(str(manifest))

        if recipe_attributes is None:
            return

        hiera_data = self._create_hiera_data(module, recipe_attributes)
        self._write_yaml_file('default.yaml', hiera_data)

    def _create_manifest(self, module_name, module_recipe):

        if len(module_recipe) == 0:
            return "node 'default' {{ class {{ {0}:}}}}".format(module_name)
        return "node 'default' {{ class {{ {0}::{1}:}}}}".\
            format(module_name, module_recipe)

    def _create_hiera_data(self, cookbook_name,
                           recipe_attributes):
        if recipe_attributes is None:
            return
        atts = {}
        for att_name, att_value in recipe_attributes.items():
            atts[cookbook_name + '::' + att_name] = att_value

        return atts

    def _write_yaml_file(self, file, data):
        with open(file, 'w') as outfile:
            outfile.write(yaml.dump(data, default_flow_style=False))
