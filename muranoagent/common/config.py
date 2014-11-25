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

import logging
import logging.config
import logging.handlers
import os
import sys

from oslo.config import cfg

from muranoagent import version

CONF = cfg.CONF

storage_opt = [
    cfg.StrOpt('storage',
               default='/var/murano/plans',
               help='Directory to store execution plans')
]

rabbit_opts = [
    cfg.StrOpt('host',
               help='The RabbitMQ broker address which used for communication '
               'with Murano guest agents.',
               default='localhost'),
    cfg.IntOpt('port', help='The RabbitMQ broker port.', default=5672),
    cfg.StrOpt('login',
               help='The RabbitMQ login.',
               default='guest'),
    cfg.StrOpt('password',
               help='The RabbitMQ password.',
               default='guest'),
    cfg.StrOpt('virtual_host',
               help='The RabbitMQ virtual host.',
               default='/'),
    cfg.BoolOpt('ssl',
                help='Boolean flag to enable SSL communication through the '
                'RabbitMQ broker between murano-engine and guest agents.',
                default=False),
    cfg.StrOpt('ca_certs',
               help='SSL cert file (valid only if SSL enabled).',
               default=''),
    cfg.StrOpt('result_routing_key',
               help='This value should be obtained from API'),
    cfg.StrOpt('result_exchange',
               help='This value must be obtained from API',
               default=''),
    cfg.StrOpt('input_queue',
               help='This value must be obtained from API',
               default='')

]

CONF.register_cli_opts(storage_opt)
CONF.register_opts(rabbit_opts, group='rabbitmq')


def parse_args(args=None, usage=None, default_config_files=None):
    version_string = version.version_info.version_string()
    CONF(args=args,
         project='muranoagent',
         version=version_string,
         usage=usage,
         default_config_files=default_config_files)


def setup_logging():
    """
    Sets up the logging options for a log with supplied name
    """

    if CONF.log_config:
        # Use a logging configuration file for all settings...
        if os.path.exists(CONF.log_config):
            logging.config.fileConfig(CONF.log_config)
            return
        else:
            raise RuntimeError("Unable to locate specified logging "
                               "config file: %s" % CONF.log_config)

    root_logger = logging.root
    if CONF.debug:
        root_logger.setLevel(logging.DEBUG)
    elif CONF.verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    formatter = logging.Formatter(CONF.log_format, CONF.log_date_format)

    if CONF.use_syslog:
        try:
            facility = getattr(logging.handlers.SysLogHandler,
                               CONF.syslog_log_facility)
        except AttributeError:
            raise ValueError(_("Invalid syslog facility"))

        handler = logging.handlers.SysLogHandler(address='/dev/log',
                                                 facility=facility)
    elif CONF.log_file:
        logfile = CONF.log_file
        if CONF.log_dir:
            logfile = os.path.join(CONF.log_dir, logfile)
        handler = logging.handlers.WatchedFileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
