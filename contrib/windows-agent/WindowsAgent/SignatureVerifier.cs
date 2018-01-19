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

using System.Configuration;
using System.IO;
using Org.BouncyCastle.Crypto;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.OpenSsl;
using Org.BouncyCastle.Security;

namespace Mirantis.Murano.WindowsAgent
{
    internal class SignatureVerifier
    {
        private readonly ISigner signer;
        private readonly byte[] salt;

        public SignatureVerifier(byte[] salt)
        {
            var keyStr = ConfigurationManager.AppSettings["engine.key"];
            if (string.IsNullOrEmpty(keyStr)) return;
            
            var reader = new StringReader(keyStr);
            var key = (RsaKeyParameters) new PemReader(reader).ReadObject();
            this.signer = SignerUtilities.GetSigner("SHA256withRSA");
            this.signer.Init(false, key);
            this.salt = salt;
        }

        public bool Verify(byte[] data, byte[] signature)
        {
            if (this.signer == null)
            {
                return true;
            }
            
            if (signature == null)
            {
                return false;
            }

            this.signer.Reset();
            this.signer.BlockUpdate(this.salt, 0, this.salt.Length);
            this.signer.BlockUpdate(data, 0, data.Length);
            return this.signer.VerifySignature(signature);
        }
    }
}
