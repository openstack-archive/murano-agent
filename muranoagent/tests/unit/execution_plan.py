# Copyright (c) 2015 Telefonica I+D.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import fixtures

from muranoagent import bunch


class ExPlanDownloable(fixtures.Fixture):
    def setUp(self):
        super(ExPlanDownloable, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout\n',
            Files={
                'ID1': {
                    'Name': 'tomcat.git',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/tomcat.git'
                },
                'ID2': {
                    'Name': 'java',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/java.git'
                },

            },
            FormatVersion='2.1.0',
            ID='ID',
            Name='Deploy Chef',
            Parameters={
                'appName': '$appName'
            },
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
                    'Files': [
                        'ID1',
                        'ID2'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True
                    },
                    'Type': 'Chef',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanApplication(fixtures.Fixture):
    def setUp(self):
        super(ExPlanApplication, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout',
            Files={
                'ID1': {
                    'Body': 'text',
                    'BodyType': 'Text',
                    'Name': 'deployTomcat.sh'
                },
                'ID2': {
                    'Body': 'dGV4dA==\n',
                    'BodyType': 'Base64',
                    'Name': 'installer'
                },
                'ID3': {
                    'Body': 'dGV4dA==\n',
                    'BodyType': 'Base64',
                    'Name': 'common.sh'
                }
            },
            FormatVersion='2.1.0',
            ID='ID',
            Name='Deploy Tomcat',
            Parameters={
                'appName': '$appName'
            },
            Scripts={
                'deploy': {
                    'EntryPoint': 'ID1',
                    'Files': [
                        'ID2',
                        'ID3'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True
                    },
                    'Type': 'Application',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanDownloableWrongFormat(fixtures.Fixture):
    def setUp(self):
        super(ExPlanDownloableWrongFormat, self).setUp()
        self.execution_plan = bunch.Bunch(
            ID='ID',
            FormatVersion='0.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanDownloableNoFiles(fixtures.Fixture):
    def setUp(self):
        super(ExPlanDownloableNoFiles, self).setUp()
        self.execution_plan = bunch.Bunch(
            ID='ID',
            FormatVersion='2.1.0',
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
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
        self.addCleanup(delattr, self, 'execution_plan')


class PuppetExPlanDownloable(fixtures.Fixture):
    def setUp(self):
        super(PuppetExPlanDownloable, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout\n',
            Files={
                'ID1': {
                    'Name': 'tomcat.git',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/tomcat.git'
                },
                'ID2': {
                    'Name': 'java',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/java.git'
                },

            },
            FormatVersion='2.0.0',
            ID='ID',
            Name='Deploy Puppet',
            Parameters={
                'appName': '$appName'
            },
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
                    'Files': [
                        'ID1',
                        'ID2'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True
                    },
                    'Type': 'Puppet',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanBerkshelf(fixtures.Fixture):
    def setUp(self):
        super(ExPlanBerkshelf, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout\n',
            Files={
                'ID1': {
                    'Name': 'tomcat.git',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/tomcat.git'
                }
            },
            FormatVersion='2.2.0',
            ID='ID',
            Name='Deploy Chef',
            Parameters={},
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
                    'Files': [
                        'ID1'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True,
                        'useBerkshelf': True
                    },
                    'Type': 'Chef',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanCustomBerskfile(fixtures.Fixture):
    def setUp(self):
        super(ExPlanCustomBerskfile, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout\n',
            Files={
                'ID1': {
                    'Name': 'tomcat.git',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/tomcat.git'
                }
            },
            FormatVersion='2.2.0',
            ID='ID',
            Name='Deploy Chef',
            Parameters={},
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
                    'Files': [
                        'ID1'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True,
                        'useBerkshelf': True,
                        'berksfilePath': 'custom/customFile'
                    },
                    'Type': 'Chef',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')


class ExPlanBerkWrongVersion(fixtures.Fixture):
    def setUp(self):
        super(ExPlanBerkWrongVersion, self).setUp()
        self.execution_plan = bunch.Bunch(
            Action='Execute',
            Body='return deploy(args.appName).stdout\n',
            Files={
                'ID1': {
                    'Name': 'tomcat.git',
                    'Type': 'Downloadable',
                    'URL': 'https://github.com/tomcat.git'
                }
            },
            FormatVersion='2.1.0',
            ID='ID',
            Name='Deploy Chef',
            Parameters={},
            Scripts={
                'deploy': {
                    'EntryPoint': 'cookbook::recipe',
                    'Files': [
                        'ID1'
                    ],
                    'Options': {
                        'captureStderr': True,
                        'captureStdout': True,
                        'useBerkshelf': True
                    },
                    'Type': 'Chef',
                    'Version': '1.0.0'
                }
            },
            Version='1.0.0'
        )
        self.addCleanup(delattr, self, 'execution_plan')
