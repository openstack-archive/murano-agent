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
import mock
import os.path

from muranoagent.common import config as cfg
from muranoagent import files_manager
from muranoagent.tests.unit import base

CONF = cfg.CONF


class TestFileManager(base.MuranoAgentTestCase):

    @mock.patch('os.path.isdir')
    @mock.patch('os.mkdir')
    @mock.patch('os.makedirs')
    def setUp(self, mock_makedir, mock_mkdir, mock_path):
        mock_path.return_value = True
        mock_mkdir.return_value = None
        mock_makedir.return_value = None
        super(TestFileManager, self).setUp()
        CONF.set_override('storage', 'cache')

    @mock.patch('os.makedirs')
    def test_get_folder_git(self, mock_path):
        """It gets the folder where the URL is a git URL."""
        mock_path.return_value = None
        files = files_manager.FilesManager(self.get_template_downloable())
        folder = files._get_file_folder("http://tomcat.git", "tomcat")
        self.assertEqual(folder,
                         os.path.normpath("cache/files/ID/files/tomcat"))

    @mock.patch('os.makedirs')
    def test_get_folder_not_git(self, mock_path):
        """It gets the folder from the URL."""
        mock_path.return_value = None
        files = files_manager.FilesManager(self.get_template_downloable())
        folder = files._get_file_folder("http://tomcat", "tomcat")
        self.assertEqual(folder,
                         os.path.normpath("cache/files/ID/files/tomcat"))

    @mock.patch("git.Git")
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_execution_plan_type_downloable_git(self, mock_makedir, mock_path,
                                                mock_git):
        """It tests an execution plan when there are files
        which should be downloable.
        """
        mock_makedir.return_value = None
        mock_path.return_value = True
        mock_git.clone.return_value = None
        template = self.get_template_downloable_git()
        files = files_manager.FilesManager(self.get_template_downloable())
        files._download_url_file(template.Files['mycoockbook'])

    @mock.patch('os.path.isdir')
    @mock.patch('os.mkdir')
    @mock.patch('os.makedirs')
    @mock.patch('__builtin__.open')
    @mock.patch('requests.get')
    def test_execution_plan_type_downloable(self, mock_requests, open_mock,
                                            mock_makedir,
                                            mock_mkdir, mock_path):
        """It tests an execution plan when there are files
        which should be downloable.
        """
        mock_path.return_value = True
        mock_mkdir.return_value = None
        mock_makedir.return_value = None
        mock_requests.return_value = None
        self._open_mock(open_mock)

        template = self.get_template_downloable()
        files = files_manager.FilesManager(self.get_template_downloable())
        files._download_url_file(template.Files['file'])

    @mock.patch('os.makedirs')
    def test_execution_plan_type_downloable_no_Url(self, mock_makedir):
        """It validates the URL."""
        mock_makedir.return_value = None
        template = bunch.Bunch(
            ID='ID',
            Files={
                'mycoockbook': {
                    'Name': 'mycoockbook.txt',
                    'Type': 'Downloadable'
                }
            }
        )
        files = files_manager.FilesManager(template)
        self.assertRaises(ValueError, files._download_url_file,
                          template.Files['mycoockbook'])

    @mock.patch("git.Git")
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_putfile_downloable(self, mock_makedir, path, mock_git):
        """It tests the putfile method when the file is a git
        URL.
        """
        path.return_value = True
        mock_git.clone.return_value = None
        mock_makedir.return_value = None
        template = self.get_template_downloable_git()
        files = files_manager.FilesManager(template)
        for file in template.get('Files'):
            files.put_file(file, 'deploy')

    @mock.patch('__builtin__.open')
    @mock.patch('os.path.lexists')
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_putfile_file(self, mock_makedir, mock_path,
                          mock_exists, open_mock):
        """It tests the putfile method."""
        mock_path.return_value = True
        mock_makedir.return_value = None
        mock_exists.return_value = True
        context_manager_mock = mock.Mock()
        open_mock.return_value = context_manager_mock
        file_mock = mock.Mock()
        file_mock.read.return_value = ''
        enter_mock = mock.Mock()
        enter_mock.return_value = file_mock
        exit_mock = mock.Mock()
        setattr(context_manager_mock, '__enter__', enter_mock)
        setattr(context_manager_mock, '__exit__', exit_mock)

        template = self.get_template_file()
        files = files_manager.FilesManager(template)
        for file in template.get('Files'):
            files.put_file(file, 'deploy')

    def get_template_downloable_git(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'mycoockbook': {
                    'Name': 'mycoockbook.txt',
                    'URL': 'git://github.com/tomcat.git',
                    'Type': 'Downloadable'
                }
            }
        )

    def get_template_downloable(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'file': {
                    'Name': 'myfile',
                    'URL': 'https://www.apache.org/licenses/LICENSE-2.0',
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
