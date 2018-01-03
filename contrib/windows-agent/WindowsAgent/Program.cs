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
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Management.Automation;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Threading;
using NLog;

namespace Mirantis.Murano.WindowsAgent
{
	[DisplayName("Murano Agent")]
	public sealed class Program : WindowsService
	{
		private static readonly Logger log = LogManager.GetCurrentClassLogger();
		private volatile bool stop;
		private Thread thread;
		private MessageSource messageSource;
		private int delayFactor = 1;
		private string plansDir;

		public static void Main(string[] args)
		{
		    Start(new Program(), args);		    
		}

		protected override void OnStart(string[] args)
		{
		    base.OnStart(args);

			log.Info("Version 0.6");

			this.messageSource = new MessageSource();

			var basePath = Path.GetDirectoryName(Process.GetCurrentProcess().MainModule.FileName);
			this.plansDir = Path.Combine(basePath, "plans");
			if (!Directory.Exists(plansDir))
			{
			    Directory.CreateDirectory(plansDir);
			}

			this.thread = new Thread(Loop);
			this.thread.Start();
		}

	    private void Loop()
		{
		    const string unknownName = "unknown";
		    var executor = new PlanExecutor(this.plansDir);
			while (!stop)
			{
				try
				{
					foreach (var file in Directory.GetFiles(this.plansDir, "*.json.result")
						.Where(file => !File.Exists(Path.Combine(this.plansDir, Path.GetFileNameWithoutExtension(file)))))
					{
						var id = Path.GetFileNameWithoutExtension(Path.GetFileNameWithoutExtension(file));
						if (id.Equals(unknownName, StringComparison.InvariantCultureIgnoreCase))
						{
							id = "";
						}

						var result = File.ReadAllText(file);
						log.Info("Sending results for {0}", id);
						messageSource.SendResult(new Message { Body = result, Id =  id });
						File.Delete(file);
					}

					var path = Directory.EnumerateFiles(this.plansDir, "*.json").FirstOrDefault();
					if (path == null)
					{
					    using (var message = messageSource.GetMessage())
					    {
					        if (message == null)
					        {
                                return;
					        }
					        var id = message.Id;
					        if (string.IsNullOrEmpty(id))
					        {
					            id = unknownName;
					        }

					        path = Path.Combine(this.plansDir, string.Format("{0}.json", id));
					        File.WriteAllText(path, message.Body);
					        log.Info("Received new execution plan {0}", id);
					    }
					}
					else
					{
						var id = Path.GetFileNameWithoutExtension(path);
						log.Info("Executing exising plan {0}", id);
					}
					
					executor.Execute(path);
					File.Delete(path);
					delayFactor = 1;

					if (stop) break;
					if (executor.RebootNeeded)
					{
						Reboot();
					}
				}
				catch (Exception exception)
				{
					WaitOnException(exception);
				}
			}
		}

		private void Reboot()
		{
			log.Info("Going for reboot!!");
			LogManager.Flush();

		
			try
			{
				PowerShell.Create().AddCommand("Restart-Computer").AddParameter("Force").Invoke();
			}
			catch (Exception exception)
			{

				log.Fatal(exception, "Reboot exception");
			}
			finally
			{
				log.Info("Waiting for reboot");
				for (var i = 0; i < 10 * 60 * 5 && !stop; i++)
				{
					Thread.Sleep(100);
				}
				log.Info("Done waiting for reboot");
			}
		}

		private void WaitOnException(Exception exception)
		{
			if (stop) return;
			log.Warn(exception, "Exception in main loop");
			var i = 0;
			while (!stop && i < 10 * (delayFactor * delayFactor))
			{
				Thread.Sleep(100);
				i++;
			}
			delayFactor = Math.Min(delayFactor + 1, 6);
		}

		protected override void OnStop()
		{
			stop = true;
			this.messageSource.Dispose();
			base.OnStop();
		}
	}
}
