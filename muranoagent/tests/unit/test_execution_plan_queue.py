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

import builtins
import fixtures

from muranoagent import execution_plan_queue

from muranoagent import app
from muranoagent import bunch
from muranoagent.common import config as cfg
from muranoagent.common.messaging import mqclient
from muranoagent import exceptions as exc
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep
from muranoagent import validation

CONF = cfg.CONF


class TestExecutionPlanQueue(base.MuranoAgentTestCase,
                             fixtures.FunctionFixture):

    @mock.patch('os.chmod')
    @mock.patch('os.path.exists')
    def setUp(self, mock_path, mock_chmod):
        super(TestExecutionPlanQueue, self).setUp()
        mock_path.side_effect = self._exists
        self.epq = execution_plan_queue.ExecutionPlanQueue()
        CONF.set_override('storage', 'cache')
        self.addCleanup(CONF.clear_override, 'storage')

    @staticmethod
    def _exists(path):
        return 'stamp' not in path

    @mock.patch('os.path.lexists')
    @mock.patch('os.path.isdir')
    @mock.patch('os.mkdir')
    def test_put_execution_plan(self, mock_makedir, mock_path,
                                mock_exists):
        mock_path.return_value = True
        mock_makedir.return_value = None
        mock_exists.return_value = True
        mock_write = mock.mock_open()

        execution_plan = 'myplan'
        signature = None
        msg_id = 1
        reply_to = 'test'
        expected_content = ('{"Data": "bXlwbGFu", "Signature": "", '
                            '"ID": 1, "ReplyTo": "test"}')
        with mock.patch.object(builtins, 'open', mock_write) as mocked_file:
            self.epq.put_execution_plan(execution_plan, signature,
                                        msg_id, reply_to)
            mocked_file().write.assert_called_once_with(expected_content)
