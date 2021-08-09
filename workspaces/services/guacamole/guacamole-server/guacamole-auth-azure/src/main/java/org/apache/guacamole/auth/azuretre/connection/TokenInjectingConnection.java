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

import java.util.Map;

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

            JSONObject credsJsonObject = getConnectionCredentialsFromProjectAPI(user, this.getConfiguration().getParameter("azure-resource-id"));

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

    private JSONObject getConnectionCredentialsFromProjectAPI(AzureTREAuthenticatedUser user, String resourceId)
            throws GuacamoleException, IOException {

        JSONObject creds = null;

        // Todo: Implement / Uncomment when the relevant API call is available for consumption
        // https://github.com/microsoft/AzureTRE/issues/561
        /*
        try {
            SSLContextBuilder builder = new SSLContextBuilder();
            builder.loadTrustMaterial(null, new TrustSelfSignedStrategy());
            SSLConnectionSocketFactory sslsf = new SSLConnectionSocketFactory(builder.build());
            CloseableHttpClient httpclient = HttpClients.custom().setSSLSocketFactory(sslsf).build();

            try {

                URI projectUri = new URI(System.getenv("PROJECT_URL"));

                // specify the host, protocol, and port
                URIBuilder uriBuilder = new URIBuilder();

                uriBuilder.setScheme(projectUri.getScheme()).setHost(projectUri.getHost()).setPort(projectUri.getPort())
                        .setPath("/api/userserviceinstancecredentials").setParameter("resourceID", resourceId);

                URI uri = uriBuilder.build();
                HttpGet httpget = new HttpGet(uri);
                httpget.addHeader("Authorization", "Bearer " + user.getAccessToken());

                CloseableHttpResponse httpResponse = httpclient.execute(httpget);

                String json = EntityUtils.toString(httpResponse.getEntity());

                if (json.length() != 0) {
                    creds = new JSONObject(json);
                }

            } catch (Exception e) {
                e.printStackTrace();
                throw new GuacamoleException(e.getMessage());
            } finally {
                // When HttpClient instance is no longer needed,
                // shut down the connection manager to ensure
                // immediate deallocation of all system resources
                httpclient.close();
            }
        } catch (Exception e) {
            e.printStackTrace();
            throw new GuacamoleException(e.getMessage());

        }
        return creds;

         */

        String json = "{\"password\": \"" + System.getenv("TEMP_PASSWORD") + "\"}";
        logger.info("returning stub creds" + json);
        creds = new JSONObject(json);

        return creds;
    }

}