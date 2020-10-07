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

from unittest import mock

from muranoagent.tests.unit import base
from muranoagent import util


class TestUtils(base.MuranoAgentTestCase):

    def test_str_to_bytes(self):
        self.assertEqual(util._to_bytes('test'), b'test')

    def test_bytes_to_bytes(self):
        self.assertEqual(util._to_bytes(b'test'), b'test')

    def test_b64encode_str(self):
        self.assertEqual(util.b64encode('test'), 'dGVzdA==')

    def test_b64encode_bytes(self):
        self.assertEqual(util.b64encode(b'test'), 'dGVzdA==')

    def test_b64decode_str(self):
        self.assertEqual(util.b64decode('dGVzdA=='), 'test')

    def test_b64decode_bytes(self):
        self.assertEqual(util.b64decode(b'dGVzdA=='), 'test')
