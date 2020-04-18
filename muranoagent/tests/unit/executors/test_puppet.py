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

from unittest import mock

import fixtures

from muranoagent import bunch
from muranoagent import exceptions as ex
from muranoagent.executors import puppet
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep


class TestPuppetExecutor(base.MuranoAgentTestCase, fixtures.TestWithFixtures):
    def setUp(self):
        super(TestPuppetExecutor, self).setUp()
        self.puppet_executor = puppet.PuppetExecutor('module::recipe')

    def test_create_manifest(self):
        node = self.puppet_executor._create_manifest('cookbook', 'recipe')
        self.assertEqual(node, self.get_manifest('cookbook', 'recipe'))

    def test_create_manifest_norecipe(self):
        node = self.puppet_executor._create_manifest('cookbook', '')
        self.assertEqual(node, self.get_manifest_norecipe('cookbook'))

    def test_create_hierdata(self):
        atts = {
            'att1': 'value1',
            'att2': 'value2'
        }

        node = self.puppet_executor._create_hiera_data('cookbook', atts)
        self.assertEqual(node, self.get_hieradata())

    @mock.patch('builtins.open')
    def test_generate_files(self, open_mock):
        self._open_mock(open_mock)
        atts = {
            'att1': 'value1',
            'att2': 'value2'
        }

        self.puppet_executor._generate_files('cookbook', 'recipe', atts)

    @mock.patch('builtins.open')
    def test_configure_puppet(self, open_mock):
        self._open_mock(open_mock)
        self.puppet_executor._configure_puppet()

    @mock.patch('subprocess.Popen')
    @mock.patch('builtins.open')
    def test_module(self, open_mock, mock_subproc_popen):
        #
        # setup
        #
        self._open_mock(open_mock)

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('ouput', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.PuppetExPlanDownloable()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.puppet_executor.load('path',
                                  script['Options'])
        self.puppet_executor.run('test')

    @mock.patch('subprocess.Popen')
    @mock.patch('builtins.open')
    def test_module_error(self, open_mock, mock_subproc_popen):
        #
        # setup
        #
        self._open_mock(open_mock)

        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('ouput', 'error'),
                 'poll.return_value': 2}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.useFixture(ep.PuppetExPlanDownloable()).execution_plan
        script = list(template['Scripts'].values())[0]
        self.puppet_executor.load('path',
                                  script['Options'])
        self.assertRaises(ex.CustomException, self.puppet_executor.run,
                          'test')

    def test_puppet_module_wrong(self):
        puppet_executor = puppet.PuppetExecutor('wrong')
        self.assertRaises(ex.CustomException, puppet_executor.run,
                          'test')

    def _stub_uuid(self, values=None):
        class FakeUUID(object):
            def __init__(self, v):
                self.hex = v

        if values is None:
            values = []
        mock_uuid4 = mock.patch('uuid.uuid4').start()
        mock_uuid4.side_effect = [FakeUUID(v) for v in values]
        return mock_uuid4

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

    def get_hieradata(self):
        return {'cookbook::att1': 'value1', 'cookbook::att2': 'value2'}

    def get_manifest(self, cookbook, recipe):
        return "node \'default\' { " \
               "class { " + cookbook + '::' + recipe + ':}}'

    def get_manifest_norecipe(self, cookbook):
        return "node \'default\' { " \
               "class { " + cookbook + ':}}'
