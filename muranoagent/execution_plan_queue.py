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

from cryptography.hazmat import backends
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from oslo_log import log as logging

from muranoagent import bunch
from muranoagent.common import config
from muranoagent import util

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ExecutionPlanQueue(object):
    plan_filename = 'plan.json'
    result_filename = 'result.json'
    stamp_filename = 'stamp'

    def __init__(self):
        self._plans_folder = os.path.join(CONF.storage, 'plans')
        if not os.path.exists(self._plans_folder):
            os.makedirs(self._plans_folder, 0o700)
        else:
            try:
                os.chmod(self._plans_folder, 0o700)
            except OSError:
                pass
        self._key = None if not CONF.engine_key \
            else serialization.load_pem_public_key(
                CONF.engine_key, backends.default_backend())
        self._load_stamp()

    def put_execution_plan(self, execution_plan, signature, msg_id, reply_to):
        timestamp = str(int(time.time() * 10000))
        # execution_plan['_timestamp'] = timestamp
        folder_path = os.path.join(self._plans_folder, timestamp)
        os.mkdir(folder_path)
        plan_file_path = os.path.join(
            folder_path, ExecutionPlanQueue.plan_filename)
        json_plan = json.dumps({
            'Data': util.b64encode(execution_plan),
            'Signature': util.b64encode(signature or ''),
            'ID': msg_id,
            'ReplyTo': reply_to
        })
        with open(plan_file_path, 'w') as out_file:
            out_file.write(json_plan)

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
        while True:
            ep_info, timestamp = self._get_first_file(
                ExecutionPlanQueue.plan_filename)
            if ep_info is None:
                return None

            try:
                data = util.b64decode(ep_info['Data'])
                if self._key:
                    signature = util.b64decode(ep_info['Signature'])
                    self._verify_signature(data, signature)

                ep = json.loads(data)
                if not isinstance(ep, dict):
                    raise ValueError('Message is not a document')

                stamp = ep.get('Stamp', -1)
                if stamp >= 0:
                    if stamp <= self._last_stamp:
                        raise ValueError('Dropping old/duplicate message')
                    self._save_stamp(stamp)

                if 'ID' not in ep:
                    ep['ID'] = ep_info['ID']
                if 'ReplyTo' not in ep:
                    ep['ReplyTo'] = ep_info['ReplyTo']

                ep['_timestamp'] = timestamp
                return bunch.Bunch(ep)
            except Exception as ex:
                LOG.exception(ex)
                self.remove(timestamp)

    def _verify_signature(self, data, signature):
        if not signature:
            raise ValueError("Required signature was not found")
        self._key.verify(
            signature,
            CONF.rabbitmq.input_queue + data,
            padding.PKCS1v15(), hashes.SHA256())

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

    def _load_stamp(self):
        plan_file_path = os.path.join(
            self._plans_folder, ExecutionPlanQueue.stamp_filename)
        if os.path.exists(plan_file_path):
            with open(plan_file_path) as f:
                self._last_stamp = int(f.read())
        else:
            self._last_stamp = 0

    def _save_stamp(self, stamp):
        plan_file_path = os.path.join(
            self._plans_folder, ExecutionPlanQueue.stamp_filename)
        with open(plan_file_path, 'w') as f:
            f.write(str(stamp))
            self._last_stamp = stamp
