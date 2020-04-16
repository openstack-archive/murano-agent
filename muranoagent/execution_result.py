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

from oslo_utils import timeutils
from oslo_utils import uuidutils

from muranoagent import exceptions as exc


class ExecutionResult(object):
    @staticmethod
    def from_result(result, execution_plan):
        if 'ID' not in execution_plan:
            raise ValueError('ID attribute is missing from execution plan')

        return {
            'FormatVersion': '2.0.0',
            'ID': uuidutils.generate_uuid(dashed=False),
            'SourceID': execution_plan.ID,
            'Action': 'Execution:Result',
            'ErrorCode': 0,
            'Body': result,
            'Time': str(timeutils.utcnow())
        }

    @staticmethod
    def from_error(error, execution_plan):
        if 'ID' not in execution_plan:
            raise ValueError('ID attribute is missing from execution plan')

        error_code = 1
        additional_info = None
        message = None
        if isinstance(error, int):
            error_code = error
        elif isinstance(error, Exception):
            message = str(error)
            if isinstance(error, exc.AgentException):
                error_code = error.error_code
                additional_info = error.additional_data

        return {
            'FormatVersion': '2.0.0',
            'ID': uuidutils.generate_uuid(dashed=False),
            'SourceID': execution_plan.ID,
            'Action': 'Execution:Result',
            'ErrorCode': error_code,
            'Body': {
                'Message': message,
                'AdditionalInfo': additional_info
            },
            'Time': str(timeutils.utcnow())
        }
