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

import sys

from muranoagent import bunch
from muranoagent import files_manager as fm
from muranoagent import script_runner


class ExecutionPlanRunner(object):
    def __init__(self, execution_plan):
        self._execution_plan = execution_plan
        self._main_script = self._prepare_script(execution_plan.Body)
        self._script_funcs = {}
        self._files_manager = fm.FilesManager(execution_plan)
        self._prepare_executors(execution_plan)

    def run(self):
        script_globals = {
            "args": bunch.Bunch(self._execution_plan.get('Parameters') or {})
        }
        script_globals.update(self._script_funcs)
        exec(self._main_script, script_globals)
        if '__execution_plan_exception' in script_globals:
            raise script_globals['__execution_plan_exception']
        return script_globals['__execution_plan_result']

    @staticmethod
    def _unindent(script, initial_indent):
        lines = script.expandtabs(4).split('\n')
        min_indent = sys.maxsize
        for line in lines:
            indent = -1
            for i, c in enumerate(line):
                if c != ' ':
                    indent = i
                    break
            if 0 <= indent < min_indent:
                min_indent = indent
        return '\n'.join([' ' * initial_indent + line[min_indent:]
                          for line in lines])

    def _prepare_executors(self, execution_plan):
        for key, value in execution_plan.Scripts.items():
            self._script_funcs[key] = script_runner.ScriptRunner(
                key, bunch.Bunch(value), self._files_manager)

    @staticmethod
    def _prepare_script(body):
        script = 'def __execution_plan_main():\n'
        script += ExecutionPlanRunner._unindent(body, 4)
        script += """
try:
    __execution_plan_result = __execution_plan_main()
except Exception as e:
    __execution_plan_exception = e
"""
        return script

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._files_manager.clear()
        return False
