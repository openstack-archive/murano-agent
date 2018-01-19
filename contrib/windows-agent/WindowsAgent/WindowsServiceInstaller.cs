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

using System.ComponentModel;
using System.Configuration.Install;
using System.Linq;
using System.Reflection;
using System.ServiceProcess;

namespace Mirantis.Murano.WindowsAgent
{
	[RunInstaller(true)]
	public class WindowsServiceInstaller : Installer
    {
		public WindowsServiceInstaller()
        {
            var processInstaller = new ServiceProcessInstaller { Account = ServiceAccount.LocalSystem };
            foreach (var type in Assembly.GetEntryAssembly().GetExportedTypes().Where(t => t.IsSubclassOf(typeof(ServiceBase))))
            {
                var nameAttribute = type.GetCustomAttributes(typeof (DisplayNameAttribute), false)
                    .Cast<DisplayNameAttribute>().FirstOrDefault();
                if(nameAttribute == null) continue;
                var serviceInstaller = new ServiceInstaller {
                    StartType = ServiceStartMode.Automatic,
                    ServiceName = nameAttribute.DisplayName,
                    DisplayName = nameAttribute.DisplayName
                };
                var descriptionAttribute = type.GetCustomAttributes(typeof(DescriptionAttribute), false)
                    .Cast<DescriptionAttribute>().FirstOrDefault();
                if(descriptionAttribute != null)
                {
                    serviceInstaller.Description = descriptionAttribute.Description;
                }

                Installers.Add(serviceInstaller);
            }

            Installers.Add(processInstaller);

        }
    }
}
