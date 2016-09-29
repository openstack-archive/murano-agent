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
	class PlanExecutor
	{
		private static readonly Logger Log = LogManager.GetCurrentClassLogger();

		class ExecutionResult
		{
			public bool IsException { get; set; }
			public object Result { get; set; }
		}

		private readonly string path;

		public PlanExecutor(string path)
		{
			this.path = path;
		}

		public bool RebootNeeded { get; set; }

		public void Execute()
		{
			RebootNeeded = false;
			var resultPath = this.path + ".result";
			Runspace runSpace = null;
			try
			{
				var plan = JsonConvert.DeserializeObject<ExecutionPlan>(File.ReadAllText(this.path));
				List<ExecutionResult> currentResults = null;
				try
				{
					currentResults = File.Exists(resultPath) ? 
						JsonConvert.DeserializeObject<List<ExecutionResult>>(File.ReadAllText(resultPath)) : 
						new List<ExecutionResult>();
				}
				catch(Exception exception)
				{
					Log.WarnException("Cannot deserialize previous execution result", exception);
					currentResults = new List<ExecutionResult>();
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
						Log.Debug("Loaded script #{0}", ++index);
					}
				}

				while (plan.Commands != null && plan.Commands.Any())
				{
					var command = plan.Commands.First();
					Log.Debug("Preparing to execute command {0}", command.Name);

					var pipeline = runSpace.CreatePipeline();
					var psCommand = new Command(command.Name);
					if (command.Arguments != null)
					{
						foreach (var kvp in command.Arguments)
						{
							var value = ConvertArgument(kvp.Value);
							psCommand.Parameters.Add(kvp.Key, value);
						}
					}

					Log.Info("Executing {0} {1}", command.Name, string.Join(" ",
						(command.Arguments ?? new Dictionary<string, object>()).Select(
							t => string.Format("{0}={1}", t.Key, t.Value == null ? "null" : t.Value.ToString()))));

					pipeline.Commands.Add(psCommand);

					try
					{
						var result = pipeline.Invoke();
						Log.Debug("Command {0} executed", command.Name);
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
						if (exception is ActionPreferenceStopException)
						{
							var apse = exception as ActionPreferenceStopException;
							if (apse.ErrorRecord != null)
							{
								additionInfo = new {
									ScriptStackTrace = apse.ErrorRecord.ScriptStackTrace,
									PositionMessage = apse.ErrorRecord.InvocationInfo.PositionMessage
								};
								exception = apse.ErrorRecord.Exception;
							}
						}


						Log.WarnException("Exception while executing command " + command.Name, exception);
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
						File.WriteAllText(resultPath, JsonConvert.SerializeObject(currentResults));
					}
				}
				runSpace.Close();
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
				File.WriteAllText(resultPath, executionResult);
			}
			catch (Exception exception)
			{
				Log.WarnException("Exception while processing execution plan", exception);
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
				Log.Debug("Finished processing of execution plan");
			}
		}

		private static object ConvertArgument(object arg)
		{
			if (arg is JArray)
			{
				var array = arg as JArray;
				return array.Select(ConvertArgument).ToArray();
			}
			else if (arg is JValue)
			{
				var value = (JValue) arg;
				return value.Value;
			}
			else if (arg is JObject)
			{
				var dict = (JObject)arg;
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
			else if (obj.BaseObject is IEnumerable<PSObject>)
			{
				return ((IEnumerable<PSObject>) obj.BaseObject).Select(SerializePsObject).ToArray();
			}
			else
			{
				return obj.BaseObject;
			}
		}
	}

}
