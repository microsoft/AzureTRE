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

import com.azure.core.credential.TokenCredential;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.TreAuthenticationProvider;
import org.apache.guacamole.auth.azuretre.TreProperties;
import org.apache.guacamole.auth.azuretre.user.TreUser;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.ConnectionGroup;
import org.apache.guacamole.net.auth.simple.SimpleConnectionGroup;
import org.apache.guacamole.net.auth.simple.SimpleDirectory;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ExecutionException;

public class ConnectionService implements AutoCloseable {

    public static final String ROOT_CONNECTION_GROUP = "ROOT";
    private static final String STATUS_DEPLOYED = "Deployed";
    private final TreProperties treConfiguration;
    private final TreUser user;
    private final Set<String> scopes;

    private SimpleConnectionGroup rootGroup;
    private SimpleDirectory<Connection> connectionDirectory;
    private Map<String, ConnectionGroup> connectionGroups = new HashMap<>();
    private TokenCredential credential;

    private final URI apiUri;

    // Logger for this class.
    private static final Logger LOGGER = LoggerFactory.getLogger(ConnectionService.class);

    public ConnectionService(TreUser user) throws GuacamoleException {
        this.user = user;
        this.treConfiguration = new TreProperties();

        apiUri = treConfiguration.getAPIUri();

        // Convert space-separated scopes.
        String scope = treConfiguration.getScope();
        this.scopes = new HashSet<>(Arrays.asList(scope.split(" ")));
    }


    @Override
    public void close() throws IOException {

    }

    public Map<String, Connection> getConnections(final TreUser user) throws GuacamoleException {
        final Map<String, Connection> connections = new TreeMap<>();
        final Map<String, GuacamoleConfiguration> configs = this.getConfigurations(user);

        for (final Map.Entry<String, GuacamoleConfiguration> config : configs.entrySet()) {
            final Connection connection = new TokenInjectingConnection(config.getKey(), config.getKey(),
                config.getValue(), true);
            connection.setParentIdentifier(TreAuthenticationProvider.ROOT_CONNECTION_GROUP);
            connections.putIfAbsent(config.getKey(), connection);
        }

        return connections;
    }

    private Map<String, GuacamoleConfiguration> getConfigurations(final TreUser user)
        throws GuacamoleException {
        final Map<String, GuacamoleConfiguration> configs = new TreeMap<>();
        if (user != null) {
            try {
                final JSONArray vmsJsonArray = getVMsFromProjectAPI(user);
                for (int i = 0; i < vmsJsonArray.length(); i++) {
                    final GuacamoleConfiguration config = new GuacamoleConfiguration();
                    final JSONObject vmJsonObject = vmsJsonArray.getJSONObject(i);
                    final JSONObject templateParameters = (JSONObject) vmJsonObject.get("properties");
                    if (templateParameters.has("hostname") && templateParameters.has("ip")) {
                        final String azureResourceId = templateParameters.getString("hostname");
                        final String ip = templateParameters.getString("ip");
                        config.setProtocol("rdp");
                        config.setParameter("hostname", ip);
                        config.setParameter("resize-method", "display-update");
                        config.setParameter("azure-resource-id", azureResourceId);
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
                    }
                }
            } catch (final Exception ex) {
                LOGGER.error("Exception getting VMs", ex);
                throw new GuacamoleException("Exception getting VMs: " + ex.getMessage());
            }
        }

        return configs;
    }

    private JSONArray getVMsFromProjectAPI(final TreUser user) throws GuacamoleException, InterruptedException, ExecutionException, MalformedURLException {
        final JSONArray virtualMachines;
        final String url = String.format("%s/api/workspaces/%s/workspace-services/%s/user-resources",
            System.getenv("API_URL"), System.getenv("WORKSPACE_ID"), System.getenv("SERVICE_ID"));
        final var client = HttpClient.newHttpClient();

        LOGGER.info("Getting access token");
        String accessToken = this.user.getToken(this.scopes);
        LOGGER.info("Getting access token - done");
        final var request = HttpRequest.newBuilder(URI.create(url))
            .header("Accept", "application/json")
            .header("Authorization", "Bearer " + accessToken)
            .timeout(Duration.ofSeconds(5))
            .build();

        final HttpResponse<String> response;
        try {
            LOGGER.info("Getting VMs list");
            response = client.send(request, HttpResponse.BodyHandlers.ofString());
            LOGGER.info("Getting VMs list - done");
        } catch (final IOException | InterruptedException ex) {
            LOGGER.error("Connection failed", ex);
            throw new GuacamoleException("Connection failed: " + ex.getMessage());
        }
        if (!response.body().isBlank()) {
            final JSONObject result = new JSONObject(response.body());
            virtualMachines = result.getJSONArray("userResources");
        } else {
            virtualMachines = new JSONArray();
        }

        return virtualMachines;
    }
}
