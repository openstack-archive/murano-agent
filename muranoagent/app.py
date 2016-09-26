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
import semantic_version
import six

from muranoagent import bunch
from muranoagent.common import config
from muranoagent.common import messaging
from muranoagent import exceptions as exc
from muranoagent import execution_plan_queue
from muranoagent import execution_plan_runner
from muranoagent import execution_result as ex_result

CONF = config.CONF

LOG = logging.getLogger(__name__)
max_format_version = semantic_version.Spec('<=2.2.0')


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
            LOG.debug("Got an execution plan '{0}':".format(str(plan)))
            self._run(plan)
            return

        next(msg_iterator)

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
                            if msg is not None and isinstance(msg.body, dict):
                                self._handle_message(msg)

                            delay = 5
                            if msg is not None:
                                msg.ack()
                                yield
            except KeyboardInterrupt:
                break
            except Exception:
                LOG.warning('Communication error', exc_info=True)
                time.sleep(delay)
                delay = min(delay * 1.2, 60)

    def _handle_message(self, msg):
        if 'ID' not in msg.body and msg.id:
            msg.body['ID'] = msg.id
        if 'ReplyTo' not in msg.body and msg.reply_to:
            msg.body['ReplyTo'] = msg.reply_to
        try:
            self._verify_plan(msg.body)
            self._queue.put_execution_plan(msg.body)
        except Exception as err:
            try:
                execution_result = ex_result.ExecutionResult.from_error(
                    err, bunch.Bunch(msg.body))
                if ('ReplyTo' in msg.body) and \
                        CONF.enable_dynamic_result_queue:
                    execution_result['ReplyTo'] = msg.body.get('ReplyTo')

                self._send_result(execution_result)
            except ValueError:
                LOG.warning('Execution result is not produced')

    def _verify_plan(self, plan):
        plan_format_version = semantic_version.Version(
            plan.get('FormatVersion', '1.0.0'))

        if plan_format_version not in max_format_version:
            # NOTE(kazitsev) this is Version in Spec not str in str
            raise exc.IncorrectFormat(
                9,
                "Unsupported format version {0} "
                "(I support versions {1})".format(
                    plan_format_version, max_format_version))

        for attr in ('Scripts', 'Files'):
            if attr not in plan:
                raise exc.IncorrectFormat(
                    2, '{0} is not in the execution plan'.format(attr))

        for attr in ('Scripts', 'Files', 'Options'):
            if attr in plan and not isinstance(
                    plan[attr], dict):
                raise exc.IncorrectFormat(
                    2, '{0} is not a dictionary'.format(attr))

        for name, script in plan.get('Scripts', {}).items():
            self._validate_script(name, script, plan_format_version, plan)

        for key, plan_file in plan.get('Files', {}).items():
            self._validate_file(plan_file, key, plan_format_version)

    def _validate_script(self, name, script, plan_format_version, plan):
        for attr in ('Type', 'EntryPoint'):
            if attr not in script or not isinstance(script[attr],
                                                    six.string_types):
                raise exc.IncorrectFormat(
                    2, 'Incorrect {0} entry in script {1}'.format(
                        attr, name))

        if plan_format_version in semantic_version.Spec('>=2.0.0,<2.1.0'):
            if script['Type'] != 'Application':
                raise exc.IncorrectFormat(
                    2, 'Type {0} is not valid for format {1}'.format(
                        script['Type'], plan_format_version))
            if script['EntryPoint'] not in plan.get('Files', {}):
                raise exc.IncorrectFormat(
                    2, 'Script {0} misses entry point {1}'.format(
                        name, script['EntryPoint']))

        if plan_format_version in semantic_version.Spec('>=2.1.0'):
            if script['Type'] not in ('Application', 'Chef', 'Puppet'):
                raise exc.IncorrectFormat(
                    2, 'Script has not a valid type {0}'.format(
                        script['Type']))
            if (script['Type'] == 'Application' and script['EntryPoint']
               not in plan.get('Files', {})):
                    raise exc.IncorrectFormat(
                        2, 'Script {0} misses entry point {1}'.format(
                            name, script['EntryPoint']))
            elif (script['Type'] != 'Application' and
                  "::" not in script['EntryPoint']):
                    raise exc.IncorrectFormat(
                        2, 'Wrong EntryPoint {0} for Puppet/Chef '
                           'executors. :: needed'.format(script['EntryPoint']))

            for option in script['Options']:
                if option in ('useBerkshelf', 'berksfilePath'):
                    if plan_format_version in semantic_version.Spec('<2.2.0'):
                        raise exc.IncorrectFormat(
                            2, 'Script has an option {0} invalid '
                               'for version {1}'.format(option,
                                                        plan_format_version))
                    elif script['Type'] != 'Chef':
                        raise exc.IncorrectFormat(
                            2, 'Script has an option {0} invalid '
                               'for type {1}'.format(option, script['Type']))

        for additional_file in script.get('Files', []):
                mns_error = ('Script {0} misses file {1}'.
                             format(name, additional_file))
                if isinstance(additional_file, dict):
                    if (list(additional_file.keys())[0] not in
                            plan.get('Files', {}).keys()):
                        raise exc.IncorrectFormat(2, mns_error)
                elif additional_file not in plan.get('Files', {}):
                    raise exc.IncorrectFormat(2, mns_error)

    def _validate_file(self, plan_file, key, format_version):
        if format_version in semantic_version.Spec('>=2.0.0,<2.1.0'):
            for plan in plan_file.keys():
                if plan in ('Type', 'URL'):
                    raise exc.IncorrectFormat(
                        2, 'Download file is {0} not valid for this '
                           'version {1}'.format(key, format_version))

        if 'Type' in plan_file:
            for attr in ('Type', 'URL', 'Name'):
                if attr not in plan_file:
                    raise exc.IncorrectFormat(
                        2,
                        'Incorrect {0} entry in file {1}'.format(attr, key))

        elif 'Body' in plan_file:
            for attr in ('BodyType', 'Body', 'Name'):
                if attr not in plan_file:
                    raise exc.IncorrectFormat(
                        2, 'Incorrect {0} entry in file {1}'.format(
                            attr, key))

            if plan_file['BodyType'] not in ('Text', 'Base64'):
                    raise exc.IncorrectFormat(
                        2, 'Incorrect BodyType in file {1}'.format(key))
        else:
            raise exc.IncorrectFormat(
                2, 'Invalid file {0}: {1}'.format(
                    key, plan_file))
