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

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.utils.URIBuilder;
import org.apache.http.conn.ssl.NoopHostnameVerifier;
import org.apache.http.conn.ssl.SSLConnectionSocketFactory;
import org.apache.http.conn.ssl.TrustSelfSignedStrategy;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.ssl.SSLContexts;
import org.apache.http.util.EntityUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.util.Map;
import java.util.TreeMap;

public class ConnectionService {
    /**
     * Logger for this class.
     */
    private static final Logger LOGGER = LoggerFactory.getLogger(ConnectionService.class);

    public Map<String, Connection> getConnections(final AzureTREAuthenticatedUser user) throws GuacamoleException {
        final Map<String, Connection> connections = new TreeMap<>();
        final Map<String, GuacamoleConfiguration> configs = this.getConfigurations(user);

        for (final Map.Entry<String, GuacamoleConfiguration> config : configs.entrySet()) {
            final Connection connection = new TokenInjectingConnection(config.getKey(), config.getKey(),
                config.getValue(), true);
            connection.setParentIdentifier(AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP);
            connections.putIfAbsent(config.getKey(), connection);
        }

        return connections;
    }

    private Map<String, GuacamoleConfiguration> getConfigurations(final AzureTREAuthenticatedUser user)
        throws GuacamoleException {
        final Map<String, GuacamoleConfiguration> configs = new TreeMap<>();
        if (user != null) {
            try {
                final JSONArray vmsJsonArray = getVMsFromProjectAPI(user);
                for (int i = 0; i < vmsJsonArray.length(); i++) {
                    final GuacamoleConfiguration config = new GuacamoleConfiguration();
                    final JSONObject vmJsonObject = vmsJsonArray.getJSONObject(i);
                    final JSONObject templateParameters = (JSONObject) vmJsonObject.get("resourceTemplateParameters");
                    if (templateParameters.has("hostname") && templateParameters.has("ip")) {
                        final String azure_resource_id = templateParameters.getString("hostname");
                        final String ip = templateParameters.getString("ip");
                        config.setProtocol("rdp");
                        config.setParameter("hostname", ip);
                        config.setParameter("resize-method", "display-update");
                        config.setParameter("azure-resource-id", azure_resource_id);
                        config.setParameter("port", "3389");
                        config.setParameter("ignore-cert", "true");
                        config.setParameter("disable-copy", System.getenv("GUAC_DISABLE_COPY"));
                        config.setParameter("disable-paste", System.getenv("GUAC_DISABLE_PASTE"));
                        config.setParameter("enable-drive", System.getenv("GUAC_ENABLE_DRIVE"));
                        config.setParameter("drive-name", System.getenv("GUAC_DRIVE_NAME"));
                        config.setParameter("drive-path", System.getenv("GUAC_DRIVE_PATH"));
                        config.setParameter("disable-download", System.getenv("GUAC_DISABLE_DOWNLOAD"));
                        LOGGER.info("Adding a VM: {}", ip);
                        configs.putIfAbsent(config.getParameter("hostname"), config);
                    } else {
                        LOGGER.info("Missing ip or hostname, skipping...");
                        break;
                    }
                }
            } catch (final Exception ex) {
                LOGGER.error("Exception getting VMs", ex);
                throw new GuacamoleException("Exception getting VMs: " + ex.getMessage());
            }
        }

        return configs;
    }

    private JSONArray getVMsFromProjectAPI(final AzureTREAuthenticatedUser user) throws GuacamoleException {
        final JSONArray virtualMachines;
        try {
            final CloseableHttpClient httpClient = HttpClients.custom()
                .setSSLSocketFactory(new SSLConnectionSocketFactory(
                    SSLContexts.custom().loadTrustMaterial(null, new TrustSelfSignedStrategy()).build(),
                    NoopHostnameVerifier.INSTANCE)
                ).build();
            try {
                final URI projectUri = new URI(System.getenv("PROJECT_URL"));
                final String serviceId = System.getenv("SERVICE_ID");
                final URIBuilder uriBuilder = new URIBuilder()
                    .setScheme(projectUri.getScheme())
                    .setHost(projectUri.getHost())
                    .setPath(String.format("api/workspace-services/%s/user-resources", serviceId));
                final URI uri = uriBuilder.build();
                final HttpGet httpget = new HttpGet(uri);
                httpget.addHeader("Authorization", "Bearer " + user.getAccessToken());
                final CloseableHttpResponse httpResponse = httpClient.execute(httpget);
                final String json = EntityUtils.toString(httpResponse.getEntity());
                if (json.length() != 0) {
                    final JSONObject result = new JSONObject(json);
                    virtualMachines = result.getJSONArray("userResources");
                } else {
                    virtualMachines = new JSONArray();
                }
            } catch (final Exception e) {
                LOGGER.error("Failed to get user resources", e);
                throw new GuacamoleException("Failed to get user resources: " + e.getMessage());
            } finally {
                httpClient.close();
            }
        } catch (final Exception e) {
            LOGGER.error("Failed to close http connection", e);
            throw new GuacamoleException("Failed to close http connection: " + e.getMessage());
        }

        return virtualMachines;
    }
}
