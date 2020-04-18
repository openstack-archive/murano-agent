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

import git
from unittest import mock

from muranoagent import bunch
from muranoagent.common import config as cfg
from muranoagent import files_manager as fmanager
from muranoagent import script_runner
from muranoagent.tests.unit import base

CONF = cfg.CONF


class TestScriptRunner(base.MuranoAgentTestCase):
    def setUp(self):
        super(TestScriptRunner, self).setUp()
        CONF.set_override('storage', 'ss')

    @mock.patch('os.path.join')
    @mock.patch("muranoagent.files_manager.FilesManager")
    @mock.patch("muranoagent.executors.Executors")
    def test_script_runner_downloable(self, mock_file_manager, mock_executors,
                                      mock_os):
        mock_file_manager.put_file.return_value = None
        mock_executors.create_executor.return_value = None
        mock_os.return_value = '/tmp/1234'
        template = self.get_template_downloable_git()
        scripts = script_runner\
            .ScriptRunner('deploy',
                          template.get('Scripts')['deploy'],
                          mock_file_manager)
        scripts._prepare_files()

    def _stub_uuid(self, values=None):
        class FakeUUID(object):
            def __init__(self, v):
                self.hex = v

        if values is None:
            values = []
        mock_uuid4 = mock.patch('uuid.uuid4').start()
        mock_uuid4.side_effect = [FakeUUID(v) for v in values]
        return mock_uuid4

    def get_template_downloable_git(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'mycoockbook': {
                    'Name': 'mycoockbook.txt',
                    'URL': 'https://github.com/tomcat.git',
                    'Type': 'Downloadable'
                }
            },
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook/recipe',
                    'Files': [
                        'https://github.com/tomcat.git',
                        {'java': 'https://github.com/java.git'}
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True
                    },
                    'Type': 'Chef',
                    'Version': '1.0.0'
                }
            }
        )

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
