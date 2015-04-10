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

import bunch
import fixtures
import json
import mock

from muranoagent.common import config as cfg
from muranoagent import exceptions as ex
from muranoagent.executors import chef
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep

CONF = cfg.CONF


class TestChefExecutor(base.MuranoAgentTestCase, fixtures.TestWithFixtures):
    def setUp(self):
        super(TestChefExecutor, self).setUp()
        self.chef_executor = chef.ChefExecutor('cookbook::recipe')

    def test_create_nodejson_noatts(self):
        """It tests the manifest without attributes."""
        node = self.chef_executor._create_manifest('cookbook', 'recipe', None)
        self.assertEqual(node, self.get_nodejs_no_atts())

    def test_create_nodejson(self):
        """It tests a manifest with attributes."""
        atts = {
            'att1': 'value1',
            'att2': 'value2'
        }

        node = self.chef_executor._create_manifest('cookbook', 'recipe', atts)
        self.assertEqual(node, self.get_nodejs_atts())

    @mock.patch('subprocess.Popen')
    @mock.patch('__builtin__.open')
    @mock.patch('os.path.exists')
    def test_cookbook(self, mock_exist, open_mock, mock_subproc_popen):
        """It tests chef executor."""
        self._open_mock(open_mock)
        mock_exist.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('ouput', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        self.chef_executor.load('path',
                                template['Scripts'].values()[0]['Options'])
        self.chef_executor.run('test')

    @mock.patch('subprocess.Popen')
    @mock.patch('__builtin__.open')
    @mock.patch('os.path.exists')
    def test_cookbook_error(self, mock_exist, open_mock, mock_subproc_popen):
        """It tests chef executor with error in the request."""
        self._open_mock(open_mock)
        mock_exist.return_value = True

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('ouput', 'error'),
                 'poll.return_value': 2}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        self.chef_executor.load('path',
                                template['Scripts'].values()[0]['Options'])
        self.assertRaises(ex.CustomException, self.chef_executor.run,
                          'test')

    def test_chef_cookbook_wrong(self):
        """It tests a wrong cookbook name."""
        chef_executor = chef.ChefExecutor('wrong')
        self.assertRaises(ex.CustomException, chef_executor.run,
                          'test')

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

    def _stub_uuid(self, values=[]):
        class FakeUUID(object):
            def __init__(self, v):
                self.hex = v

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

    def get_nodejs_atts(self):
        return json.dumps({
            "run_list": [
                "recipe[cookbook::recipe]"
            ],
            "cookbook": {
                "att1": "value1",
                "att2": "value2"
            }
        })

    def get_nodejs_no_atts(self):
        return json.dumps({
            "run_list": [
                "recipe[cookbook::recipe]"
            ]
        })
