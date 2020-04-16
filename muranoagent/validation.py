# Copyright (c) 2017 Mirantis Inc.
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

import semantic_version

from muranoagent import exceptions as exc


max_format_version = semantic_version.Spec('<=2.2.0')


def validate_plan(plan):
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
        _validate_script(name, script, plan_format_version, plan)

    for key, plan_file in plan.get('Files', {}).items():
        _validate_file(plan_file, key, plan_format_version)


def _validate_script(name, script, plan_format_version, plan):
    for attr in ('Type', 'EntryPoint'):
        if attr not in script or not isinstance(script[attr], str):
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
        mns_error = ('Script {0} misses file {1}'.format(
            name, additional_file))
        if isinstance(additional_file, dict):
            if (list(additional_file.keys())[0] not in
                    plan.get('Files', {}).keys()):
                raise exc.IncorrectFormat(2, mns_error)
        elif additional_file not in plan.get('Files', {}):
            raise exc.IncorrectFormat(2, mns_error)


def _validate_file(plan_file, key, format_version):
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
                2, 'Incorrect BodyType in file {0}'.format(key))
    else:
        raise exc.IncorrectFormat(
            2, 'Invalid file {0}: {1}'.format(
                key, plan_file))
