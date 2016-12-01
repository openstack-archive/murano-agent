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

import anyjson
from oslo_log import log as logging

LOG = logging.getLogger("murano-common.messaging")


class Message(object):
    def __init__(self, connection=None, message_handle=None):
        self._body = None
        self._connection = connection
        self._message_handle = message_handle
        if message_handle:
            self.id = message_handle.properties.get('message_id')
            self._reply_to = message_handle.properties.get('reply_to')
        else:
            self.id = None
            self._reply_to = None

        try:
            if message_handle:
                if isinstance(message_handle.body, bytes):
                    message_handle.body = message_handle.body.decode('utf-8')
                self.body = anyjson.loads(message_handle.body)
            else:
                self.body = None
        except ValueError:
            self.body = None
            LOG.exception('Message is not in JSON format')

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value or ''

    @property
    def reply_to(self):
        return self._reply_to

    def ack(self):
        self._message_handle.ack()
