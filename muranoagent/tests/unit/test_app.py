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
import mock

from muranoagent import app
from muranoagent import bunch
from muranoagent.common import config as cfg
from muranoagent import exceptions as exc
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep

CONF = cfg.CONF


class TestApp(base.MuranoAgentTestCase, fixtures.FunctionFixture):

    @mock.patch('os.path.exists')
    def setUp(self, mock_path):
        super(TestApp, self).setUp()
        mock_path.return_value = True
        self.agent = app.MuranoAgent()
        CONF.set_override('storage', 'cache')

    def test_verify_execution_plan_downloable(self):
        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        self.agent._verify_plan(template)

    def test_verify_execution_plan_wrong_format(self):
        template = bunch.Bunch(
            ID='ID',
            FormatVersion='0.0.0',
        )
        self.assertRaises(exc.IncorrectFormat,
                          self.agent._verify_plan, template)

    def test_verify_over_max_execution_plan(self):
        template = self.useFixture(ep.ExPlanApplication()).execution_plan
        template['FormatVersion'] = '1000.0.0'
        self.assertRaises(exc.IncorrectFormat,
                          self.agent._verify_plan, template)

    def test_verify_execution_application(self):
        template = self.useFixture(ep.ExPlanApplication()).execution_plan
        self.agent._verify_plan(template)

    def test_verify_wrong_execution_application(self):
        template = self.useFixture(ep.ExPlanApplication()).execution_plan
        template['Files']['ID1'] = {
            'Name': 'tomcat.git',
            'Type': 'Downloadable',
            'URL': 'https://github.com/tomcat.git'
        }
        template['FormatVersion'] = '2.0.0'
        self.assertRaises(exc.IncorrectFormat,
                          self.agent._verify_plan, template)

    def test_verify_execution_plan_no_files(self):
        template = self.useFixture(ep.ExPlanDownloableNoFiles()).execution_plan
        self.assertRaises(exc.IncorrectFormat,
                          self.agent._verify_plan, template)

    def test_verify_execution_plan_berkshelf(self):
        template = self.useFixture(ep.ExPlanBerkshelf()).execution_plan
        self.agent._verify_plan(template)

    def test_verify_execution_plan_berkshelf_wrong_version(self):
        template = self.useFixture(ep.ExPlanBerkWrongVersion()).execution_plan
        self.assertRaises(exc.IncorrectFormat,
                          self.agent._verify_plan, template)
