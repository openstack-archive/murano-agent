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


class AgentException(Exception):
    def __init__(self, code, message=None, additional_data=None):
        self._error_code = code
        self._additional_data = additional_data
        super(AgentException, self).__init__(message)

    @property
    def error_code(self):
        return self._error_code

    @property
    def additional_data(self):
        return self._additional_data


class CustomException(AgentException):
    def __init__(self, code, message=None, additional_data=None):
        super(CustomException, self).__init__(
            code + 100, message, additional_data)


class IncorrectFormat(AgentException):
    pass
