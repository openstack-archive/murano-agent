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
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Text;
using Newtonsoft.Json.Linq;
using NLog;
using Newtonsoft.Json;

namespace Mirantis.Murano.WindowsAgent
{
    internal class PlanExecutor
	{
		private static readonly Logger log = LogManager.GetCurrentClassLogger();
	    private long lastStamp = -1;

		class ExecutionResult
		{
			public bool IsException { get; set; }
			public object Result { get; set; }
		}

		private readonly string baseDir;

		public PlanExecutor(string baseDir)
		{
			this.baseDir = baseDir;
		}

		public bool RebootNeeded { get; set; }

		public void Execute(string path)
		{
			RebootNeeded = false;
			var resultPath = path + ".result";
			var tmpResultPath = resultPath + ".tmp";
			Runspace runSpace = null;
			try
			{
				var plan = JsonConvert.DeserializeObject<ExecutionPlan>(File.ReadAllText(path));
				List<ExecutionResult> currentResults;
				try
				{
					currentResults = File.Exists(tmpResultPath) ? 
						JsonConvert.DeserializeObject<List<ExecutionResult>>(File.ReadAllText(tmpResultPath)) : 
						new List<ExecutionResult>();
				}
				catch(Exception exception)
				{
					log.Warn(exception, "Cannot deserialize previous execution result");
					currentResults = new List<ExecutionResult>();
				}

			    var lastStamp = GetLastStamp();
			    if (plan.Stamp > 0 && plan.Stamp <= lastStamp)
			    {
			        log.Warn("Dropping old/duplicate plan");
			        return;
			    }

			    runSpace = RunspaceFactory.CreateRunspace();
				runSpace.Open();

				var runSpaceInvoker = new RunspaceInvoke(runSpace);
				runSpaceInvoker.Invoke("Set-ExecutionPolicy Unrestricted");
				if (plan.Scripts != null)
				{
					var index = 0;
					foreach (var script in plan.Scripts)
					{
						runSpaceInvoker.Invoke(Encoding.UTF8.GetString(Convert.FromBase64String(script)));
						log.Debug("Loaded script #{0}", ++index);
					}
				}

				while (plan.Commands != null && plan.Commands.Any())
				{
					var command = plan.Commands.First();
					log.Debug("Preparing to execute command {0}", command.Name);

					var pipeline = runSpace.CreatePipeline();
				    if (command.Name != null)
				    {
				        var psCommand = new Command(command.Name);
				        if (command.Arguments != null)
				        {
				            foreach (var kvp in command.Arguments)
				            {
				                var value = ConvertArgument(kvp.Value);
				                psCommand.Parameters.Add(kvp.Key, value);
				            }
				        }

				        log.Info("Executing {0} {1}", command.Name, string.Join(" ",
				            (command.Arguments ?? new Dictionary<string, object>()).Select(
				                t => string.Format("{0}={1}", t.Key, t.Value?.ToString() ?? "null"))));

				        pipeline.Commands.Add(psCommand);
				    }

				    try
					{
						var result = pipeline.Invoke();
						log.Debug("Command {0} executed", command.Name);
						if (result != null)
						{
							currentResults.Add(new ExecutionResult {
								IsException = false,
								Result = result.Where(obj => obj != null).Select(SerializePsObject).ToList()
							});
						}
					}
					catch (Exception exception)
					{
						object additionInfo = null;
					    var apse = exception as ActionPreferenceStopException;
					    if (apse?.ErrorRecord != null)
					    {
					        additionInfo = new {
					            ScriptStackTrace = apse.ErrorRecord.ScriptStackTrace,
					            PositionMessage = apse.ErrorRecord.InvocationInfo.PositionMessage
					        };
					        exception = apse.ErrorRecord.Exception;
					    }


					    log.Warn(exception, "Exception while executing command " + command.Name);
						currentResults.Add(new ExecutionResult
						{
							IsException = true,
							Result = new[] {
								exception.GetType().FullName, exception.Message, command.Name, additionInfo
							}
						});
						break;
					}
					finally
					{
						plan.Commands.RemoveFirst();
						File.WriteAllText(path, JsonConvert.SerializeObject(plan));
					    File.WriteAllText(tmpResultPath, JsonConvert.SerializeObject(currentResults));
					}
				}
				runSpace.Close();
			    if (plan.Stamp > 0)
			    {
                    SetLastStamp(plan.Stamp);
			    }
				var executionResult = JsonConvert.SerializeObject(new ExecutionResult {
					IsException = false,
					Result = currentResults
				}, Formatting.Indented);

				if (plan.RebootOnCompletion > 0)
				{
					if (plan.RebootOnCompletion == 1)
					{
						RebootNeeded = !currentResults.Any(t => t.IsException);
					}
					else
					{
						RebootNeeded = true;
					}
				}
				File.Delete(tmpResultPath);
			    File.WriteAllText(resultPath, executionResult);
			}
			catch (Exception exception)
			{
				log.Warn(exception, "Exception while processing execution plan");
				File.WriteAllText(resultPath, JsonConvert.SerializeObject(new ExecutionResult {
					IsException = true,
					Result = exception.Message
				}, Formatting.Indented));
			}
			finally
			{
				if (runSpace != null)
				{
					try
					{
						runSpace.Close();
					}
					catch
					{}
				}
				log.Debug("Finished processing of execution plan");
			}
		}

		private static object ConvertArgument(object arg)
		{
			switch (arg)
			{
			    case JArray array:
			        return array.Select(ConvertArgument).ToArray();
			    case JValue value:
			        return value.Value;
			    case JObject dict:
			        var result = new Hashtable();
			        foreach (var item in dict)
			        {
			            result.Add(item.Key, ConvertArgument(item.Value));
			        }
			        return result;
			}

		    return arg;
		}
	
		private static object SerializePsObject(PSObject obj)
		{
		    if (obj.BaseObject is PSCustomObject)
			{
				var result = new Dictionary<string, object>();
				foreach (var property in obj.Properties.Where(p => p.IsGettable))
				{
					try
					{
						result[property.Name] = property.Value.ToString();
					}
					catch
					{
					}
				}
				return result;
			}

		    if (obj.BaseObject is IEnumerable<PSObject> objects)
		    {
		        return objects.Select(SerializePsObject).ToArray();
		    }

		    return obj.BaseObject;
		}

	    private long GetLastStamp()
	    {
	        if (this.lastStamp >= 0)
	        {
	            return this.lastStamp;
	        }

	        var path = Path.Combine(this.baseDir, "stamp.txt");
	        if (File.Exists(path))
	        {
	            try
	            {
	                var stampData = File.ReadAllText(path);
	                this.lastStamp = long.Parse(stampData);
	            }
	            catch (Exception e)
	            {
	                this.lastStamp = 0;
	            }
	        }
	        else
	        {
	            this.lastStamp = 0;
	        }

	        return this.lastStamp;
	    }

	    private void SetLastStamp(long value)
	    {
	        var path = Path.Combine(this.baseDir, "stamp.txt");
	        try
	        {
	            File.WriteAllText(path, value.ToString());
	        }
	        catch (Exception e)
	        {
	            log.Error(e, "Cannot persist last stamp");
	            throw;
	        }
	        finally
	        {
	            this.lastStamp = value;
	        }
	    }
	}


}
