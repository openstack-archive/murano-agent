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
import sys
import time
import types

import bunch
import semver

from muranoagent.common import config
from muranoagent.common import messaging
from muranoagent import exceptions as exc
from muranoagent import execution_plan_queue
from muranoagent import execution_plan_runner
from muranoagent import execution_result as ex_result
from muranoagent.openstack.common import log as logging
from muranoagent.openstack.common import service

CONF = config.CONF

LOG = logging.getLogger(__name__)
format_version = '2.0.0'


class MuranoAgent(service.Service):
    def __init__(self):
        self._queue = execution_plan_queue.ExecutionPlanQueue()
        super(MuranoAgent, self).__init__()

    @staticmethod
    def _load_package(name):
        try:
            LOG.debug('Loading plugin %s', name)
            __import__(name)
        except Exception:
            LOG.warn('Cannot load package %s', name, exc_info=True)
            pass

    def _load(self):
        path = os.path.join(os.path.dirname(__file__), 'executors')
        sys.path.insert(1, path)
        for entry in os.listdir(path):
            package_path = os.path.join(path, entry)
            if os.path.isdir(package_path):
                MuranoAgent._load_package(entry)

    def start(self):
        self._load()
        msg_iterator = self._wait_plan()
        while True:
            try:
                self._loop_func(msg_iterator)
            except Exception as ex:
                LOG.exception(ex)
                time.sleep(5)

    def _loop_func(self, msg_iterator):
        result, timestamp = self._queue.get_execution_plan_result()
        if result is not None:
            if self._send_result(result):
                self._queue.remove(timestamp)
            return

        plan = self._queue.get_execution_plan()
        if plan is not None:
            LOG.debug("Got an execution plan '{0}':".format(str(plan)))
            self._run(plan)
            return

        msg_iterator.next()

    def _run(self, plan):
        with execution_plan_runner.ExecutionPlanRunner(plan) as runner:
            try:
                result = runner.run()
                execution_result = ex_result.ExecutionResult.from_result(
                    result, plan)
                self._queue.put_execution_result(execution_result, plan)
            except Exception as ex:
                LOG.exception('Error running execution plan')
                execution_result = ex_result.ExecutionResult.from_error(ex,
                                                                        plan)
                self._queue.put_execution_result(execution_result, plan)

    def _send_result(self, result):
        with self._create_rmq_client() as mq:
            msg = messaging.Message()
            msg.body = result
            msg.id = result.get('SourceID')
            mq.send(message=msg,
                    key=CONF.rabbitmq.result_routing_key,
                    exchange=CONF.rabbitmq.result_exchange)
        return True

    def _create_rmq_client(self):
        rabbitmq = CONF.rabbitmq
        connection_params = {
            'login': rabbitmq.login,
            'password': rabbitmq.password,
            'host': rabbitmq.host,
            'port': rabbitmq.port,
            'virtual_host': rabbitmq.virtual_host,
            'ssl': rabbitmq.ssl,
            'ca_certs': rabbitmq.ca_certs.strip() or None
        }
        return messaging.MqClient(**connection_params)

    def _wait_plan(self):
        delay = 5
        while True:
            try:
                with self._create_rmq_client() as mq:
                    with mq.open(CONF.rabbitmq.input_queue,
                                 prefetch_count=1) as subscription:
                        while True:
                            msg = subscription.get_message(timeout=5)
                            if msg is not None and isinstance(msg.body, dict):
                                self._handle_message(msg)

                            if msg is not None:
                                msg.ack()
                                yield
                            delay = 5
            except KeyboardInterrupt:
                break
            except Exception:
                LOG.warn('Communication error', exc_info=True)
                time.sleep(delay)
                delay = min(delay * 1.2, 60)

    def _handle_message(self, msg):
        print(msg.body)
        if 'ID' not in msg.body and msg.id:
            msg.body['ID'] = msg.id
        err = self._verify_plan(msg.body)
        if err is None:
            self._queue.put_execution_plan(msg.body)
        else:
            try:
                execution_result = ex_result.ExecutionResult.from_error(
                    err, bunch.Bunch(msg.body))

                self._send_result(execution_result)
            except ValueError:
                LOG.warn('Execution result is not produced')

    def _verify_plan(self, plan):
        plan_format_version = plan.get('FormatVersion', '1.0.0')
        if semver.compare(plan_format_version, '2.0.0') > 0 or \
                semver.compare(plan_format_version, format_version) < 0:
            range_str = 'in range 2.0.0-{0}'.format(plan_format_version) \
                if format_version != '2.0.0' \
                else 'equal to {0}'.format(format_version)
            return exc.AgentException(
                3,
                'Unsupported format version {0} (must be {1})'.format(
                    plan_format_version, range_str))

        for attr in ('Scripts', 'Files', 'Options'):
            if attr is plan and not isinstance(
                    plan[attr], types.DictionaryType):
                return exc.AgentException(
                    2, '{0} is not a dictionary'.format(attr))

        for name, script in plan.get('Scripts', {}).items():
            for attr in ('Type', 'EntryPoint'):
                if attr not in script or not isinstance(
                        script[attr], types.StringTypes):
                    return exc.AgentException(
                        2, 'Incorrect {0} entry in script {1}'.format(
                            attr, name))
            if not isinstance(script.get('Options', {}), types.DictionaryType):
                return exc.AgentException(
                    2, 'Incorrect Options entry in script {0}'.format(name))

            if script['EntryPoint'] not in plan.get('Files', {}):
                return exc.AgentException(
                    2, 'Script {0} misses entry point {1}'.format(
                        name, script['EntryPoint']))

            for additional_file in script.get('Files', []):
                if additional_file not in plan.get('Files', {}):
                    return exc.AgentException(
                        2, 'Script {0} misses file {1}'.format(
                            name, additional_file))

        for key, plan_file in plan.get('Files', {}).items():
            for attr in ('BodyType', 'Body', 'Name'):
                if attr not in plan_file:
                    return exc.AgentException(
                        2, 'Incorrect {0} entry in file {1}'.format(
                            attr, key))

            if plan_file['BodyType'] not in ('Text', 'Base64'):
                return exc.AgentException(
                    2, 'Incorrect BodyType in file {1}'.format(key))

        return None
