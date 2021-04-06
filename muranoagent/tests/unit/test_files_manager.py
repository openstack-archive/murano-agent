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

import os.path
from unittest import mock

from muranoagent import bunch
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

    def test_is_svn(self):
        files = files_manager.FilesManager(self.get_template_downloable(1))
        self.assertTrue(files._is_svn_repository("https://sdfa/svn/ss"))

    def test_is_svn_first(self):
        files = files_manager.FilesManager(self.get_template_downloable(2))
        self.assertTrue(files._is_svn_repository("svn://test"))

    def test_is_svn_wrong_http_protocol(self):
        files = files_manager.FilesManager(self.get_template_downloable(3))
        self.assertFalse(files._is_svn_repository("httpp://sdfa/svn/ss"))

    def test_is_svn_wrong_svn_slash(self):
        files = files_manager.FilesManager(self.get_template_downloable(4))
        self.assertFalse(files._is_svn_repository("svn:sdfa/svn/ss"))

    @mock.patch("git.Git")
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_execution_plan_type_downloable_git(self, mock_makedir, mock_path,
                                                mock_git):
        """Test an execution plan with downloadable git files

        """
        mock_makedir.return_value = None
        mock_path.return_value = True
        mock_git.clone.return_value = None
        template = self.get_template_downloable_git()
        files = files_manager.FilesManager(self.get_template_downloable(5))
        files._download_url_file(template.Files['mycoockbook'], "script")

    @mock.patch('os.path.isdir')
    @mock.patch('os.mkdir')
    @mock.patch('os.makedirs')
    @mock.patch('builtins.open')
    @mock.patch('requests.get')
    def test_execution_plan_type_downloable(self, mock_requests, open_mock,
                                            mock_makedir,
                                            mock_mkdir, mock_path):
        """Test an execution plan with downloadable files

        """
        mock_path.return_value = True
        mock_mkdir.return_value = None
        mock_makedir.return_value = None
        mock_requests.return_value = None
        self._open_mock(open_mock)

        template = self.get_template_downloable(6)
        files = files_manager.FilesManager(self.get_template_downloable(6))
        files._download_url_file(template.Files['file'], "script")

    @mock.patch('subprocess.Popen')
    @mock.patch('os.makedirs')
    def test_execution_plan_type_svn(self, mock_makedir, mock_subproc_popen):
        """Test an execution plan with svn files."""
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('ouput', 'ok'),
                 'poll.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        template = self.get_template_svn()
        files = files_manager.FilesManager(template)
        files._download_url_file(template.Files['file'], "script")

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
                          template.Files['mycoockbook'], "script")

    @mock.patch("git.Git")
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.lexists')
    def test_putfile_downloable(self, mock_exists, mock_makedir,
                                path, mock_git):
        """It tests the putfile method when the file is a git URL.

        """
        path.return_value = True
        mock_git.clone.return_value = None
        mock_makedir.return_value = None
        mock_exists.return_value = True
        template = self.get_template_downloable_git()
        files = files_manager.FilesManager(template)
        for file in template.get('Files'):
            files.put_file(file, 'deploy')

    @mock.patch('builtins.open')
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

    def get_template_downloable(self, file_id):
        return bunch.Bunch(
            ID='ID',
            Files={
                'file': {
                    'Name': 'myfile',
                    'URL': 'https://www.apache.org/licenses',
                    'Type': 'Downloadable'
                }
            }
        )

    def get_template_svn(self):
        return bunch.Bunch(
            ID='ID',
            Files={
                'file': {
                    'Name': 'svn',
                    'URL': 'https://mysvn/svn/repo',
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
