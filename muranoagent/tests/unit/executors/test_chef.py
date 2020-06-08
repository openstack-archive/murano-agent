#    Copyright (c) 2015 Telefonica I+D
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import fixtures
import json
import os
from unittest import mock
from unittest.mock import ANY

from muranoagent import bunch
from muranoagent import exceptions as ex
from muranoagent.executors import chef
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep


class TestChefExecutor(base.MuranoAgentTestCase, fixtures.TestWithFixtures):
    def setUp(self):
        super(TestChefExecutor, self).setUp()
        self.chef_executor = chef.ChefExecutor('cookbook::recipe')

    def test_create_nodejson_noatts(self):
        """It tests the manifest without attributes."""
        node = self.chef_executor._create_manifest('cookbook', 'recipe', None)
        self.assertEqual(json.loads(node), self.get_node_no_atts())

    def test_create_nodejson(self):
        """It tests a manifest with attributes."""
        atts = {
            'att1': 'value1',
            'att2': 'value2'
        }

        node = self.chef_executor._create_manifest('cookbook', 'recipe', atts)
        self.assertEqual(json.loads(node), self.get_node_atts())

    @mock.patch('subprocess.Popen')
    @mock.patch('builtins.open')
    @mock.patch('os.path.exists')
    @mock.patch('os.path.isdir')
    def test_cookbook(self, mock_isdir, mock_exist, open_mock,
                      mock_subproc_popen):
        """It tests chef executor."""
        self._open_mock(open_mock)
        mock_exist.return_value = True
        mock_isdir.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        script = list(template['Scripts'].values())
        self.chef_executor.load('path',
                                script[0]['Options'])
        self.chef_executor.run('test')

    @mock.patch('subprocess.Popen')
    @mock.patch('builtins.open')
    @mock.patch('os.path.exists')
    @mock.patch('os.path.isdir')
    def test_cookbook_error(self, mock_isdir, mock_exist, open_mock,
                            mock_subproc_popen):
        """It tests chef executor with error in the request."""
        self._open_mock(open_mock)
        mock_exist.return_value = True
        mock_isdir.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'),
                 'poll.return_value': 2}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.chef_executor.load('path',
                                script['Options'])
        self.assertRaises(ex.CustomException, self.chef_executor.run,
                          'test')

    def test_chef_cookbook_wrong(self):
        """It tests a wrong cookbook name."""
        chef_executor = chef.ChefExecutor('wrong')
        self.assertRaises(ex.CustomException, chef_executor.run,
                          'test')

    def test_chef_no_berkshelf(self):
        """It tests the cookbook path if Berkshelf is not enabled"""
        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.chef_executor.load('path',
                                script['Options'])
        cookbook_path = self.chef_executor._create_cookbook_path('cookbook')
        self.assertEqual(cookbook_path, os.path.abspath('path'))

    @mock.patch('subprocess.Popen')
    @mock.patch('os.path.isfile')
    def test_chef_berkshelf_default_berksfile(self, mock_isfile,
                                              mock_subproc_popen):
        """It tests Berkshelf usage if no Berksfile path is provided"""
        mock_isfile.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanBerkshelf()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.chef_executor.load('path',
                                script['Options'])
        self.chef_executor.module_name = 'test'
        cookbook_path = self.chef_executor._create_cookbook_path('cookbook')

        self.assertEqual(cookbook_path,
                         os.path.abspath('path/berks-cookbooks'))
        expected_command = 'berks vendor --berksfile={0} {1}'.format(
                           os.path.abspath('path/cookbook/Berksfile'),
                           cookbook_path)
        mock_subproc_popen.assert_called_once_with(expected_command,
                                                   cwd=ANY,
                                                   shell=ANY,
                                                   stdout=ANY,
                                                   stderr=ANY,
                                                   universal_newlines=ANY)

    @mock.patch('subprocess.Popen')
    @mock.patch('os.path.isfile')
    def test_chef_berkshelf_custom_berksfile(self, mock_isfile,
                                             mock_subproc_popen):
        """It tests Berkshelf usage if a custom Berksfile is provided"""
        mock_isfile.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanCustomBerskfile()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.chef_executor.load('path',
                                script['Options'])
        self.chef_executor.module_name = 'test'
        cookbook_path = self.chef_executor._create_cookbook_path('cookbook')

        self.assertEqual(cookbook_path,
                         os.path.abspath('path/berks-cookbooks'))
        expected_command = 'berks vendor --berksfile={0} {1}'.format(
                           os.path.abspath('path/custom/customFile'),
                           cookbook_path)
        mock_subproc_popen.assert_called_once_with(expected_command,
                                                   cwd=ANY,
                                                   shell=ANY,
                                                   stdout=ANY,
                                                   stderr=ANY,
                                                   universal_newlines=ANY)

    @mock.patch('subprocess.Popen')
    @mock.patch('os.path.isfile')
    def test_chef_berkshelf_error(self, mock_isfile,
                                  mock_subproc_popen):
        """It tests if Berkshelf throws an error"""
        mock_isfile.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'),
                 'poll.return_value': 2}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanBerkshelf()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.chef_executor.load('path',
                                script['Options'])
        self.chef_executor.module_name = 'test'
        self.assertRaises(ex.CustomException,
                          self.chef_executor._create_cookbook_path,
                          'cookbook')

    def _open_mock(self, open_mock):
        context_manager_mock = mock.Mock()
        open_mock.return_value = context_manager_mock
        file_mock = mock.Mock()
        file_mock.read.return_value = ''
        enter_mock = mock.Mock()
        enter_mock.return_value = file_mock
        exit_mock = mock.Mock()
        setattr(context_manager_mock, '__enter__', enter_mock)
        setattr(context_manager_mock, '__exit__', exit_mock)

    def _stub_uuid(self, values=None):
        class FakeUUID(object):
            def __init__(self, v):
                self.hex = v

        if values is None:
            values = []
        mock_uuid4 = mock.patch('uuid.uuid4').start()
        mock_uuid4.side_effect = [FakeUUID(v) for v in values]
        return mock_uuid4

    def get_template_downloable(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'file': {
                    'Name': 'myfile',
                    'URL': 'https://github.com'
                           '/apache/tomcat/blob/trunk/LICENSE',
                    'Type': 'Downloadable'
                }
            }
        )

    def get_template_file(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'test': {
                    'Body': 'dGV4dA==\n',
                    'BodyType': 'Base64',
                    'Name': 'installer'
                }
            }
        )

    def get_node_atts(self):
        return {
            "run_list": [
                "recipe[cookbook::recipe]"
            ],
            "cookbook": {
                "att1": "value1",
                "att2": "value2"
            }
        }

    def get_node_no_atts(self):
        return {
            "run_list": [
                "recipe[cookbook::recipe]"
            ]
        }
