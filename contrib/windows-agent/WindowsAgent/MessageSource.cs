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
using System.Configuration;
using System.Net.Security;
using System.Security.Authentication;
using System.Text;
using NLog;
using RabbitMQ.Client;

namespace Mirantis.Murano.WindowsAgent
{
    internal class MessageSource : IDisposable
	{
		private static readonly Logger log = LogManager.GetCurrentClassLogger();
		private static readonly ConnectionFactory connectionFactory;
	    private static readonly string queueName;
		private IConnection currentConnecton;
	    private readonly SignatureVerifier signatureVerifier;
        

		static MessageSource()
		{
		    var ssl = new SslOption {
		        Enabled = bool.Parse(ConfigurationManager.AppSettings["rabbitmq.ssl"] ?? "false"),
		        Version = SslProtocols.Default,
                AcceptablePolicyErrors = bool.Parse(ConfigurationManager.AppSettings["rabbitmq.allowInvalidCA"] ?? "true") ? 
                    SslPolicyErrors.RemoteCertificateChainErrors : SslPolicyErrors.None
		    };

		    var sslServerName = ConfigurationManager.AppSettings["rabbitmq.sslServerName"] ?? "";
		    ssl.ServerName = sslServerName;
            if (String.IsNullOrWhiteSpace(sslServerName))
            {
                ssl.AcceptablePolicyErrors |= SslPolicyErrors.RemoteCertificateNameMismatch;
            }

            connectionFactory = new ConnectionFactory {
                HostName = ConfigurationManager.AppSettings["rabbitmq.host"] ?? "localhost",
                UserName = ConfigurationManager.AppSettings["rabbitmq.user"] ?? "guest",
                Password = ConfigurationManager.AppSettings["rabbitmq.password"] ??"guest",
                Protocol = Protocols.DefaultProtocol,
                VirtualHost = ConfigurationManager.AppSettings["rabbitmq.vhost"] ?? "/",
                Port = int.Parse(ConfigurationManager.AppSettings["rabbitmq.port"] ?? "5672"),
                RequestedHeartbeat = 10,
                Ssl = ssl
            };
		    queueName = ConfigurationManager.AppSettings["rabbitmq.inputQueue"];
		}
		
		public MessageSource()
		{
			this.signatureVerifier = new SignatureVerifier(Encoding.ASCII.GetBytes(queueName));
		}

		public Message GetMessage()
		{
			try
			{
				IConnection connection;
				lock (this)
				{
					connection = this.currentConnecton = this.currentConnecton ?? connectionFactory.CreateConnection();
				}
				var session = connection.CreateModel();
				session.BasicQos(0, 1, false);
			    var consumer = new QueueingBasicConsumer(session);
				var consumeTag = session.BasicConsume(queueName, false, consumer);

			    while (true)
			    {
			        var e = consumer.Queue.Dequeue();
			        Action ackFunc = delegate
			        {
			            session.BasicAck(e.DeliveryTag, false);
			            session.BasicCancel(consumeTag);
			            session.Close();
			        };

			        byte[] signature = null;
			        if (e.BasicProperties.Headers.ContainsKey("signature"))
			        {
			            signature = (byte[]) e.BasicProperties.Headers["signature"];
			        }

			        if (this.signatureVerifier.Verify(e.Body, signature))
			        {
			            return new Message(ackFunc) {
			                Body = Encoding.UTF8.GetString(e.Body),
			                Id = e.BasicProperties.MessageId,
			            };
			        }

			        log.Warn("Dropping message with invalid/missing signature");
			        session.BasicReject(e.DeliveryTag, false);
			    }
			}
			catch (Exception)
			{
			    if (this.currentConnecton == null) return null;
			    Dispose();
			    throw;
			}
		}

		public void SendResult(Message message)
		{
			var exchangeName = ConfigurationManager.AppSettings["rabbitmq.resultExchange"] ?? "";
			var resultRoutingKey = ConfigurationManager.AppSettings["rabbitmq.resultRoutingKey"] ?? "-execution-results";
			bool durable = bool.Parse(ConfigurationManager.AppSettings["rabbitmq.durableMessages"] ?? "true");

			try
			{
				IConnection connection;
				lock (this)
				{
					connection = this.currentConnecton = this.currentConnecton ?? connectionFactory.CreateConnection();
				}
				var session = connection.CreateModel();
				var basicProperties = session.CreateBasicProperties();
				basicProperties.Persistent = durable;
				basicProperties.MessageId = message.Id;
				basicProperties.ContentType = "application/json";
				session.BasicPublish(exchangeName, resultRoutingKey, basicProperties, Encoding.UTF8.GetBytes(message.Body));
				session.Close();
			}
			catch (Exception)
			{
				Dispose();
				throw;
			}
		}

		public void Dispose()
		{
			lock (this)
			{
				try
				{
				    var connection = this.currentConnecton;
				    this.currentConnecton = null;
				    connection.Close();
				}
				catch
				{
				}
			}
		}
	}
}
