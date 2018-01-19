// Licensed to the Apache Software Foundation (ASF) under one or more
// contributor license agreements. See the NOTICE file distributed with
// this work for additional information regarding copyright ownership.
// The ASF licenses this file to you under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with
// the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System;
using System.Configuration.Install;
using System.Reflection;
using System.ServiceProcess;
using NLog;

namespace Mirantis.Murano.WindowsAgent
{
    public class ServiceManager
    {
        private readonly string serviceName;

        public ServiceManager(string serviceName)
        {
            this.serviceName = serviceName;
        }

        private static readonly Logger log = LogManager.GetCurrentClassLogger();

        public bool Restart(string[] args, TimeSpan timeout)
        {
            var service = new ServiceController(serviceName);
            try
            {
                var millisec1 = TimeSpan.FromMilliseconds(Environment.TickCount);

                service.Stop();
                service.WaitForStatus(ServiceControllerStatus.Stopped, timeout);
                log.Info("Service is stopped");

                // count the rest of the timeout
                var millisec2 = TimeSpan.FromMilliseconds(Environment.TickCount);
                timeout = timeout - (millisec2 - millisec1);

                service.Start(args);
                service.WaitForStatus(ServiceControllerStatus.Running, timeout);
                log.Info("Service has started");
                return true;
            }
            catch (Exception ex)
            {
                log.Error(ex, "Cannot restart service " + serviceName);
                return false;
            }
        }

        public bool Stop(TimeSpan timeout)
        {
            var service = new ServiceController(serviceName);
            try
            {
                service.Stop();
                service.WaitForStatus(ServiceControllerStatus.Stopped, timeout);
                return true;
            }
            catch (Exception ex)
            {
                log.Error(ex, "Cannot stop service " + serviceName);
                return false;
            }
        }

        public bool Start(string[] args, TimeSpan timeout)
        {
            var service = new ServiceController(serviceName);
            try
            {
                service.Start(args);
                service.WaitForStatus(ServiceControllerStatus.Running, timeout);
                return true;
            }
            catch (Exception ex)
            {
                log.Error(ex, "Cannot start service " + serviceName);
                return false;
            }
        }

        public bool Install()
        {
            try
            {
                ManagedInstallerClass.InstallHelper(
                    new[] { Assembly.GetEntryAssembly().Location });
            }
            catch(Exception ex)
            {
                log.Error(ex, "Cannot install service " + serviceName);
                return false;
            }
            return true;
        }

        public bool Uninstall()
        {
            try
            {
                ManagedInstallerClass.InstallHelper(
                    new[] { "/u", Assembly.GetEntryAssembly().Location });
            }
            catch (Exception ex)
            {
                log.Error(ex, "Cannot uninstall service " + serviceName);
                return false;
            }
            return true;
        }

    }
    
}
