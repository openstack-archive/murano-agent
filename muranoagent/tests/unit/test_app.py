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
import ssl as ssl_module

from muranoagent import app
from muranoagent import bunch
from muranoagent.common import config as cfg
from muranoagent.common.messaging import mqclient
from muranoagent import exceptions as exc
from muranoagent.tests.unit import base
from muranoagent.tests.unit import execution_plan as ep
from muranoagent import validation

CONF = cfg.CONF


class TestApp(base.MuranoAgentTestCase, fixtures.FunctionFixture):

    @mock.patch('os.chmod')
    @mock.patch('os.path.exists')
    def setUp(self, mock_path, mock_chmod):
        super(TestApp, self).setUp()
        mock_path.side_effect = self._exists
        self.agent = app.MuranoAgent()
        CONF.set_override('storage', 'cache')
        self.addCleanup(CONF.clear_override, 'storage')

    @staticmethod
    def _exists(path):
        return 'stamp' not in path

    def test_verify_execution_plan_downloable(self):
        template = self.useFixture(ep.ExPlanDownloable()).execution_plan
        self.agent._verify_plan(template)

    def test_verify_execution_plan_wrong_format(self):
        template = bunch.Bunch(
            ID='ID',
            FormatVersion='0.0.0',
        )
        self.assertRaises(exc.IncorrectFormat,
                          validation.validate_plan, template)

    def test_verify_over_max_execution_plan(self):
        template = self.useFixture(ep.ExPlanApplication()).execution_plan
        template['FormatVersion'] = '1000.0.0'
        self.assertRaises(exc.IncorrectFormat,
                          validation.validate_plan, template)

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
                          validation.validate_plan, template)

    def test_verify_execution_plan_no_files(self):
        template = self.useFixture(ep.ExPlanDownloableNoFiles()).execution_plan
        self.assertRaises(exc.IncorrectFormat,
                          validation.validate_plan, template)

    def test_verify_execution_plan_berkshelf(self):
        template = self.useFixture(ep.ExPlanBerkshelf()).execution_plan
        self.agent._verify_plan(template)

    def test_verify_execution_plan_berkshelf_wrong_version(self):
        template = self.useFixture(ep.ExPlanBerkWrongVersion()).execution_plan
        self.assertRaises(exc.IncorrectFormat,
                          validation.validate_plan, template)

    @mock.patch.object(mqclient, 'random', autospec=True)
    @mock.patch.object(mqclient, 'kombu', autospec=True)
    def test_rmq_client_initialization_with_ssl_version(self, mock_kombu,
                                                        mock_random):
        expected_heartbeat = 20  # 20 = 20 + 20 * 0, due to mocked value below.
        mock_random.random.return_value = 0

        ssl_versions = (
            ('tlsv1', getattr(ssl_module, 'PROTOCOL_TLSv1', None)),
            ('tlsv1_1', getattr(ssl_module, 'PROTOCOL_TLSv1_1', None)),
            ('tlsv1_2', getattr(ssl_module, 'PROTOCOL_TLSv1_2', None)),
            ('sslv2', getattr(ssl_module, 'PROTOCOL_SSLv2', None)),
            ('sslv23', getattr(ssl_module, 'PROTOCOL_SSLv23', None)),
            ('sslv3', getattr(ssl_module, 'PROTOCOL_SSLv3', None)))
        exception_count = 0

        for ssl_name, ssl_version in ssl_versions:
            ssl_kwargs = {
                'login': 'test_login',
                'password': 'test_password',
                'host': 'test_host',
                'port': 'test_port',
                'virtual_host': 'test_virtual_host',
                'ssl': True,
                'ssl_version': ssl_name,
                'ca_certs': ['cert1'],
                'insecure': False
            }

            # If a ssl_version is not valid, a RuntimeError is thrown.
            # According to the ssl_version docs in config.py, certain versions
            # of TLS may be available depending on the system. So, just
            # check that at least 1 ssl_version works.
            if ssl_version is None:
                e = self.assertRaises(RuntimeError, mqclient.MqClient,
                                      **ssl_kwargs)
                self.assertEqual('Invalid SSL version: %s' % ssl_name,
                                 e.__str__())
                exception_count += 1
                continue

            self.ssl_client = mqclient.MqClient(**ssl_kwargs)

            mock_kombu.Connection.assert_called_once_with(
                'amqp://{0}:{1}@{2}:{3}/{4}'.format(
                    'test_login', 'test_password', 'test_host', 'test_port',
                    'test_virtual_host'),
                heartbeat=expected_heartbeat,
                ssl={'ca_certs': ['cert1'],
                     'cert_reqs': ssl_module.CERT_REQUIRED,
                     'ssl_version': ssl_version})
            self.assertEqual(
                mock_kombu.Connection(), self.ssl_client._connection)
            self.assertIsNone(self.ssl_client._channel)
            self.assertFalse(self.ssl_client._connected)
            mock_kombu.Connection.reset_mock()

        # Check that at least one ssl_version worked.
        self.assertGreater(len(ssl_versions), exception_count)
