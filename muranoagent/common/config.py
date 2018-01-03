# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
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

"""
Routines for configuring Murano-Agent
"""

from oslo_config import cfg
from oslo_log import log as logging

from muranoagent import version

CONF = cfg.CONF

opts = [
    cfg.StrOpt('storage',
               default='/var/murano/plans',
               help='Directory to store execution plans'),

    cfg.StrOpt('engine_key',
               help='Public key of murano-engine')
]

message_routing_opt = cfg.BoolOpt(
    'enable_dynamic_result_queue',
    help='Enable taking dynamic result queue from task field reply_to',
    default=False)


rabbit_opts = [
    cfg.HostAddressOpt('host',
                       help='The RabbitMQ broker address which used for '
                            'communication with Murano guest agents.',
                       default='localhost'),
    cfg.IntOpt('port', help='The RabbitMQ broker port.', default=5672),
    cfg.StrOpt('login',
               help='The RabbitMQ login.',
               default='guest'),
    cfg.StrOpt('password',
               help='The RabbitMQ password.',
               secret=True,
               default='guest'),
    cfg.StrOpt('virtual_host',
               help='The RabbitMQ virtual host.',
               default='/'),
    cfg.BoolOpt('ssl',
                help='Boolean flag to enable SSL communication through the '
                'RabbitMQ broker between murano-engine and guest agents.',
                default=False),
    cfg.StrOpt('ssl_version',
               default='',
               help='SSL version to use (valid only if SSL enabled). '
                    'Valid values are TLSv1 and SSLv23. SSLv2, SSLv3, '
                    'TLSv1_1, and TLSv1_2 may be available on some '
                    'distributions.'),
    cfg.StrOpt('ca_certs',
               help='SSL cert file (valid only if SSL enabled).',
               default=''),
    cfg.BoolOpt('insecure', default=False,
                help='This option explicitly allows Murano to perform '
                     '"insecure" SSL connections to RabbitMQ'),
    cfg.StrOpt('result_routing_key',
               help='This value should be obtained from API'),
    cfg.StrOpt('result_exchange',
               help='This value must be obtained from API',
               default=''),
    cfg.StrOpt('input_queue',
               help='This value must be obtained from API',
               default='')

]

CONF.register_opts(opts)
CONF.register_cli_opt(message_routing_opt)
CONF.register_opts(rabbit_opts, group='rabbitmq')
logging.register_options(CONF)


def parse_args(args=None, usage=None, default_config_files=None):
    version_string = version.version_info.version_string()
    CONF(args=args,
         project='muranoagent',
         version=version_string,
         usage=usage,
         default_config_files=default_config_files)
