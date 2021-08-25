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

import com.azure.core.http.HttpClient;
import com.azure.core.http.netty.NettyAsyncHttpClientBuilder;
import com.azure.identity.ManagedIdentityCredentialBuilder;
import com.azure.security.keyvault.secrets.SecretClient;
import com.azure.security.keyvault.secrets.SecretClientBuilder;
import java.io.IOException;
import java.util.Map;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.GuacamoleTunnel;
import org.apache.guacamole.net.auth.simple.SimpleConnection;
import org.apache.guacamole.protocol.GuacamoleClientInformation;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
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
                fullConfig.setParameter("username", credsJsonObject.get("username").toString());
                fullConfig.setParameter("password", credsJsonObject.get("password").toString());
                this.setConfiguration(fullConfig);
            }

        } catch (IOException e) {

            e.printStackTrace();
            throw new GuacamoleException("IOException getting VMs: " + e.getMessage());
        }
        return super.connect(info, tokens);

    }

    private JSONObject getConnectionCredentialsFromProjectAPI(String resourceName)
            throws IOException {

        JSONObject credentials;
        String username = null;
        String password = null;

        try {
            logger.info("Loading credentials from Azure Key Vault for secret " + resourceName + ".");
            String keyVaultUri = System.getenv("KEYVAULT_URL");
            HttpClient httpClient = new NettyAsyncHttpClientBuilder().build();
            SecretClient secretClient = new SecretClientBuilder()
                    .vaultUrl(keyVaultUri)
                    .credential(new ManagedIdentityCredentialBuilder().httpClient(httpClient).build())
                    .httpClient(httpClient)
                    .buildClient();

            String secretName = String.format("%s-admin-credentials", resourceName);
            String keyVaultResponse = secretClient.getSecret(secretName).getValue();
            String[] resourceCredentials = keyVaultResponse.split("\\n");
            if (resourceCredentials.length == 2) {
                username = resourceCredentials[0];
                password = resourceCredentials[1];
            }

        } catch (Exception e) {
            logger.error(e.getMessage(), e);
        }

        String json = "{\"username\": \"" + username + "\",\"password\": \"" + password + "\"}";
        credentials = new JSONObject(json);

        return credentials;
    }

}