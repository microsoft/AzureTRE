/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.apache.guacamole.auth.azuretre.connection;

import java.net.URI;
import java.util.Map;

import com.azure.identity.DefaultAzureCredential;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.azure.security.keyvault.secrets.SecretClient;
import com.azure.security.keyvault.secrets.SecretClientBuilder;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.GuacamoleTunnel;
import org.apache.guacamole.protocol.GuacamoleClientInformation;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.apache.guacamole.net.auth.simple.SimpleConnection;

import java.io.IOException;

import org.json.JSONObject;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TokenInjectingConnection extends SimpleConnection {

    private static final Logger logger = LoggerFactory.getLogger(TokenInjectingConnection.class);

    private final AzureTREAuthenticatedUser user;

    public TokenInjectingConnection(String name, String identifier, GuacamoleConfiguration config,
                                    boolean interpretTokens, AzureTREAuthenticatedUser user) {
        super(name, identifier, config, interpretTokens);
        this.user = user;
    }

    @Override
    public GuacamoleTunnel connect(GuacamoleClientInformation info, Map<String, String> tokens)
            throws GuacamoleException {

        try {

            JSONObject credsJsonObject = getConnectionCredentialsFromProjectAPI(this.getConfiguration().getParameter("azure-resource-id"));

            if (credsJsonObject != null) {

                GuacamoleConfiguration fullConfig = this.getFullConfiguration();
                fullConfig.setParameter("password", credsJsonObject.get("password").toString());
                this.setConfiguration(fullConfig);
            }

        } catch (IOException e) {

            e.printStackTrace();
            throw new GuacamoleException("IOException getting VMs: " + e.getMessage());
        }
        return super.connect(info, tokens);

    }

    private JSONObject getConnectionCredentialsFromProjectAPI(String resourceId)
            throws GuacamoleException, IOException {

        JSONObject creds;
        String resourceCreds = null;

        try {
            logger.info("Loading credentials from Azure Key Vault for secret " + resourceId + ".");
            String keyVaultUri = String.format("https://kv-gucacamole-%s-%s.vault.azure.net"
                    , System.getenv("TRE_ID")
                    , System.getenv("WORKSPACE_ID"));

            DefaultAzureCredential credential = new DefaultAzureCredentialBuilder().build();
            SecretClient secretClient = new SecretClientBuilder()
                    .vaultUrl(keyVaultUri)
                    .credential(credential)
                    .buildClient();

            String secretName = String.format("%s-admin-credentials");
            resourceCreds = secretClient.getSecret(secretName).getValue();


        } catch (Exception e) {
            logger.error(e.getMessage(), e);
        }


        String json = "{\"password\": \"" + resourceCreds + "\"}";
        logger.info("Returning stub creds" + json);
        creds = new JSONObject(json);

        return creds;
    }

}