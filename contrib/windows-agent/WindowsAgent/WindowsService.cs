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
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reflection;
using System.ServiceProcess;
using NLog;

namespace Mirantis.Murano.WindowsAgent
{
    public abstract class WindowsService : ServiceBase
    {
        private static readonly Logger log = LogManager.GetCurrentClassLogger();

	    protected static void Start(WindowsService service, string[] arguments)
        {
            Directory.SetCurrentDirectory(Path.GetDirectoryName(Assembly.GetEntryAssembly().Location));

			if (arguments.Contains("/install", StringComparer.OrdinalIgnoreCase))
            {
                new ServiceManager(service.ServiceName).Install();
            }
			else if (arguments.Contains("/uninstall", StringComparer.OrdinalIgnoreCase))
			{
                new ServiceManager(service.ServiceName).Uninstall();
            }
			else if (arguments.Contains("/start", StringComparer.OrdinalIgnoreCase))
			{
                new ServiceManager(service.ServiceName).Start(Environment.GetCommandLineArgs(), TimeSpan.FromMinutes(1));
            }
			else if (arguments.Contains("/stop", StringComparer.OrdinalIgnoreCase))
			{
                new ServiceManager(service.ServiceName).Stop(TimeSpan.FromMinutes(1));
            }
			else if (arguments.Contains("/restart", StringComparer.OrdinalIgnoreCase))
			{
                new ServiceManager(service.ServiceName).Restart(Environment.GetCommandLineArgs(), TimeSpan.FromMinutes(1));
            }
			else if (!arguments.Contains("/console", StringComparer.OrdinalIgnoreCase))
			{
				Run(service);
			}
			else
			{
				try
				{
					Console.Title = service.ServiceName;
					service.OnStart(Environment.GetCommandLineArgs());
					service.WaitForExitSignal();
				}
				finally
				{
					service.OnStop();
					service.Dispose();
				}
			}
        }
        
        protected WindowsService()
        {
            var displayNameAttribute =
                this.GetType().GetCustomAttributes(typeof (DisplayNameAttribute), false).Cast<DisplayNameAttribute>().
                    FirstOrDefault();
            if(displayNameAttribute != null)
            {
                ServiceName = displayNameAttribute.DisplayName;
            }
        }


        protected virtual void WaitForExitSignal()
        {
            Console.WriteLine("Press ESC to exit");
            while (Console.ReadKey(true).Key != ConsoleKey.Escape)
            {
            }
        }

		protected override void OnStart(string[] args)
		{
			log.Info("Service {0} started", ServiceName);

			base.OnStart(args);
		}

		protected override void OnStop()
		{
			log.Info("Service {0} exited", ServiceName);
			base.OnStop();
		}
    }
}
