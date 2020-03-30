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

from oslo_log import log as logging
from oslo_service import service
from oslo_utils import strutils

from muranoagent.common import config
from muranoagent.common import messaging
from muranoagent import execution_plan_queue
from muranoagent import execution_plan_runner
from muranoagent import execution_result as ex_result
from muranoagent import validation

CONF = config.CONF

LOG = logging.getLogger(__name__)


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
            LOG.warning('Cannot load package %s', name, exc_info=True)
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
            LOG.debug("Got an execution plan '{0}':".format(
                strutils.mask_password(str(plan))))
            if self._verify_plan(plan):
                self._run(plan)
            return

        next(msg_iterator)

    def _verify_plan(self, plan):
        try:
            validation.validate_plan(plan)
            return True
        except Exception as err:
            try:
                execution_result = ex_result.ExecutionResult.from_error(
                    err, plan)
                if 'ReplyTo' in plan and CONF.enable_dynamic_result_queue:
                    execution_result['ReplyTo'] = plan.ReplyTo

                self._send_result(execution_result)
            except ValueError:
                LOG.warning('Execution result is not produced')
            finally:
                return False

    def _run(self, plan):
        try:
            with execution_plan_runner.ExecutionPlanRunner(plan) as runner:
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
            routing_key = CONF.rabbitmq.result_routing_key
            if ('ReplyTo' in result) and CONF.enable_dynamic_result_queue:
                routing_key = result.pop('ReplyTo')
            mq.send(message=msg,
                    key=routing_key,
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
            'ssl_version': rabbitmq.ssl_version,
            'ca_certs': rabbitmq.ca_certs.strip() or None,
            'insecure': rabbitmq.insecure
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
                            if msg is not None:
                                try:
                                    self._queue.put_execution_plan(
                                        msg.body,
                                        msg.signature,
                                        msg.id,
                                        msg.reply_to)
                                finally:
                                    msg.ack()

                            delay = 5
                            if msg is not None:
                                yield
            except KeyboardInterrupt:
                break
            except Exception:
                LOG.warning('Communication error', exc_info=True)
                time.sleep(delay)
                delay = min(delay * 1.2, 60)
