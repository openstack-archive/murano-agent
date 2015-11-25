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

import json
import os
import shutil
import time


from muranoagent import bunch
from muranoagent.common import config

CONF = config.CONF


class ExecutionPlanQueue(object):
    plan_filename = 'plan.json'
    result_filename = 'result.json'

    def __init__(self):
        self._plans_folder = os.path.join(CONF.storage, 'plans')
        if not os.path.exists(self._plans_folder):
            os.makedirs(self._plans_folder)

    def put_execution_plan(self, execution_plan):
        timestamp = str(int(time.time() * 10000))
        # execution_plan['_timestamp'] = timestamp
        folder_path = os.path.join(self._plans_folder, timestamp)
        os.mkdir(folder_path)
        file_path = os.path.join(
            folder_path, ExecutionPlanQueue.plan_filename)
        with open(file_path, 'w') as out_file:
            out_file.write(json.dumps(execution_plan))

    def _get_first_timestamp(self, filename):
        def predicate(folder):
            path = os.path.join(self._plans_folder, folder, filename)
            return os.path.exists(path)

        timestamps = [
            name for name in os.listdir(self._plans_folder)
            if predicate(name)
        ]
        timestamps.sort()
        return None if len(timestamps) == 0 else timestamps[0]

    def _get_first_file(self, filename):
        timestamp = self._get_first_timestamp(filename)
        if not timestamp:
            return None, None
        path = os.path.join(self._plans_folder, timestamp, filename)
        with open(path) as json_file:
            return json.loads(json_file.read()), timestamp

    def get_execution_plan(self):
        ep, timestamp = self._get_first_file(ExecutionPlanQueue.plan_filename)
        if ep is None:
            return None
        ep['_timestamp'] = timestamp
        return bunch.Bunch(ep)

    def put_execution_result(self, result, execution_plan):
        timestamp = execution_plan['_timestamp']
        if 'ReplyTo' in execution_plan:
            result['ReplyTo'] = execution_plan.get('ReplyTo')
        path = os.path.join(
            self._plans_folder, timestamp,
            ExecutionPlanQueue.result_filename)
        with open(path, 'w') as out_file:
            out_file.write(json.dumps(result))

    def remove(self, timestamp):
        path = os.path.join(self._plans_folder, timestamp)
        shutil.rmtree(path)

    def get_execution_plan_result(self):
        return self._get_first_file(
            ExecutionPlanQueue.result_filename)
