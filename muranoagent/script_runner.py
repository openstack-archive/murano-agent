# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from muranoagent import executors as exe


class FunctionRunner(object):
    def __init__(self, name, script_runner):
        self._name = name
        self._script_executor = script_runner

    def __call__(self, *args, **kwargs):
        return self._script_executor.execute_function(
            self._name, *args, **kwargs)


class ScriptRunner(object):
    def __init__(self, name, script_info, files_manager):
        self._name = name
        self._executor = self._get_executor(script_info['Type'], name,
                                            script_info['EntryPoint'])
        self._script_info = script_info
        self._script_loaded = False
        self._files_manager = files_manager

    def __call__(self, *args, **kwargs):
        return self.execute_function(None, *args, **kwargs)

    def _get_executor(self, script_type, script_name, entry_point):
        create_executor = exe.Executors.create_executor
        if script_type != 'Application':
            executor = create_executor(script_type, entry_point)
        else:
            executor = create_executor(script_type, script_name)
        if executor is None:
            raise ValueError('The application type in {0} is not a valid '
                             'executor {1}'.format(script_name, script_type))
        return executor

    def execute_function(self, name, *args, **kwargs):
        self._load()
        return self._executor.run(name, *args, **kwargs)

    def __getattr__(self, item):
        return FunctionRunner(item, self)

    def _load(self):
        if not self._script_loaded:
            self._executor.load(
                self._prepare_files(),
                self._script_info.get("Options") or {})
            self._script_loaded = True

    def _prepare_files(self):
        for file_id in self._script_info.get('Files', []):
            self._files_manager.put_file(file_id, self._name)

        if self._script_info["Type"] == 'Application':
            return self._files_manager.put_file(
                self._script_info["EntryPoint"], self._name)
        return os.path.join(self._files_manager._cache_folder, self._name)
