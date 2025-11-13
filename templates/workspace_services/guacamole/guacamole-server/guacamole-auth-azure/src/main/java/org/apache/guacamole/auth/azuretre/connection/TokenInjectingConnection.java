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
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.azure.security.keyvault.secrets.SecretClient;
import com.azure.security.keyvault.secrets.SecretClientBuilder;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.net.GuacamoleTunnel;
import org.apache.guacamole.net.auth.simple.SimpleConnection;
import org.apache.guacamole.protocol.GuacamoleClientInformation;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * Guacamole connection which injects credentials from Azure Key Vault before
 * establishing the tunnel.
 */
public final class TokenInjectingConnection extends SimpleConnection {

    /** Logger instance. */
    private static final Logger LOGGER = LoggerFactory.getLogger(
        TokenInjectingConnection.class);

    /**
     * Creates a new connection wrapper that can inject credentials retrieved
     * from secure storage.
     *
     * @param name             display name for the connection.
     * @param identifier       connection identifier.
     * @param config           backing configuration.
     * @param interpretTokens  whether tokens should be interpreted.
     */
    public TokenInjectingConnection(
        final String name,
        final String identifier,
        final GuacamoleConfiguration config,
        final boolean interpretTokens) {
        super(name, identifier, config, interpretTokens);
    }

    @Override
    public GuacamoleTunnel connect(
        final GuacamoleClientInformation info,
        final Map<String, String> tokens) throws GuacamoleException {
        final JSONObject credentials =
            getConnectionCredentialsFromProjectAPI(
                getConfiguration().getParameter("azure-resource-id"));
        final GuacamoleConfiguration fullConfig = getFullConfiguration();
        fullConfig.setParameter("username", credentials.getString("username"));
        fullConfig.setParameter("password", credentials.getString("password"));
        setConfiguration(fullConfig);

        try {
            return super.connect(info, tokens);
        } finally {
            // Clear credentials from configuration after connection attempt.
            fullConfig.setParameter("username", null);
            fullConfig.setParameter("password", null);
        }
    }

    private JSONObject getConnectionCredentialsFromProjectAPI(
        final String resourceName) throws GuacamoleException {
        final JSONObject credentials = new JSONObject();
        String username = null;
        String password = null;

        try {
            LOGGER.debug(
                "Loading credentials from Azure Key Vault for secret {}",
                resourceName);
            final String keyVaultUri = System.getenv("KEYVAULT_URL");
            final String managedIdentityClientId = System.getenv(
                "MANAGED_IDENTITY_CLIENT_ID");

            // Build an HTTP client explicitly for the credential builder.
            final HttpClient httpClient = new NettyAsyncHttpClientBuilder()
                .build();

            final SecretClient secretClient = new SecretClientBuilder()
                .vaultUrl(keyVaultUri)
                .credential(new DefaultAzureCredentialBuilder()
                    .managedIdentityClientId(managedIdentityClientId)
                    .httpClient(httpClient)
                    .build())
                .httpClient(httpClient)
                .buildClient();

            final String secretName = String.format(
                "%s-admin-credentials",
                resourceName);
            final String keyVaultResponse = secretClient
                .getSecret(secretName)
                .getValue();
            final String[] resourceCredentials = keyVaultResponse.split("\\n");

            if (resourceCredentials.length == 2) {
                username = resourceCredentials[0];
                password = resourceCredentials[1];
            } else {
                LOGGER.error("Invalid credential format from Key Vault");
                throw new GuacamoleException(
                    "Failed to retrieve valid credentials");
            }
        } catch (final GuacamoleException ex) {
            throw ex;
        } catch (final Exception ex) {
            LOGGER.error(
                "Key Vault credential fetch failed: {}",
                ex.getClass().getSimpleName());
            LOGGER.debug("Detailed error", ex);
            throw new GuacamoleException(
                "Failed to retrieve credentials from secure storage");
        }

        credentials.put("username", username);
        credentials.put("password", password);
        return credentials;
    }
}
