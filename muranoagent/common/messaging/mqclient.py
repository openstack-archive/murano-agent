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

import random
import ssl as ssl_module

import eventlet
import json
import kombu
from oslo_service import sslutils

from muranoagent.common.messaging import subscription


class MqClient(object):
    def __init__(self, login, password, host, port, virtual_host,
                 ssl=False, ssl_version=None, ca_certs=None, insecure=False):
        ssl_params = None

        if ssl:
            cert_reqs = ssl_module.CERT_REQUIRED
            if insecure:
                if ca_certs:
                    cert_reqs = ssl_module.CERT_OPTIONAL
                else:
                    cert_reqs = ssl_module.CERT_NONE

            ssl_params = {
                'ca_certs': ca_certs,
                'cert_reqs': cert_reqs
            }

            if ssl_version:
                key = ssl_version.lower()
                try:
                    ssl_params['ssl_version'] = sslutils._SSL_PROTOCOLS[key]
                except KeyError:
                    raise RuntimeError("Invalid SSL version: %s" % ssl_version)

        # Time interval after which RabbitMQ will disconnect client if no
        # heartbeats were received. Usually client sends 2 heartbeats during
        # this interval. Using random to make it less lucky that many agents
        # ping RabbitMQ simultaneously
        heartbeat_rate = 20 + 20 * random.random()

        self._connection = kombu.Connection(
            'amqp://{0}:{1}@{2}:{3}/{4}'.format(
                login,
                password,
                host,
                port,
                virtual_host
            ), ssl=ssl_params, heartbeat=heartbeat_rate
        )
        self._channel = None
        self._connected = False
        self._exception = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._connected = False
        else:
            self.close()
        return False

    def connect(self):
        self._connection.connect()
        self._channel = self._connection.channel()
        if not self._connected:
            self._connected = True
            eventlet.spawn(self._heartbeater)

    def close(self):
        if self._connected:
            self._connection.close()
            self._connected = False

    def _check_exception(self):
        ex = self._exception
        if ex:
            self._exception = None
            raise ex

    def _heartbeater(self):
        while self._connected:
            eventlet.sleep(1)
            try:
                self._connection.heartbeat_check()
            except Exception as ex:
                self._exception = ex
                self._connected = False

    def declare(self, queue, exchange='', enable_ha=False, ttl=0):
        self._check_exception()
        if not self._connected:
            raise RuntimeError('Not connected to RabbitMQ')

        queue_arguments = {}
        if enable_ha is True:
            # To use mirrored queues feature in RabbitMQ 2.x
            # we need to declare this policy on the queue itself.
            #
            # Warning: this option has no effect on RabbitMQ 3.X,
            # to enable mirrored queues feature in RabbitMQ 3.X, please
            # configure RabbitMQ.
            queue_arguments['x-ha-policy'] = 'all'
        if ttl > 0:
            queue_arguments['x-expires'] = ttl

        exchange = kombu.Exchange(exchange, type='direct', durable=True)
        queue = kombu.Queue(queue, exchange, queue, durable=False,
                            queue_arguments=queue_arguments)
        bound_queue = queue(self._connection)
        bound_queue.declare()

    def send(self, message, key, exchange=''):
        self._check_exception()
        if not self._connected:
            raise RuntimeError('Not connected to RabbitMQ')

        producer = kombu.Producer(self._connection)
        producer.publish(
            exchange=str(exchange),
            routing_key=str(key),
            body=json.dumps(message.body),
            message_id=str(message.id)
        )

    def open(self, queue, prefetch_count=1):
        self._check_exception()
        if not self._connected:
            raise RuntimeError('Not connected to RabbitMQ')

        return subscription.Subscription(self._connection, queue,
                                         prefetch_count, self._check_exception)
