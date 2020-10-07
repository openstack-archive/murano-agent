#    Copyright (c) 2014 Mirantis, Inc.
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

import base64


def _to_bytes(string):
    """Coerce a string into bytes

    Since Python 3 now handles bytes and str differently, this helper
    will coerce a string to bytes if possible for use with base64
    """
    try:
        string = string.encode()
    except AttributeError:
        pass
    return string


def b64encode(string):
    """Base64 encode a string to a string"""
    string = _to_bytes(string)
    return base64.b64encode(string).decode()


def b64decode(string):
    """Base64 decode a string to a string"""
    string = _to_bytes(string)
    return base64.b64decode(string).decode()
