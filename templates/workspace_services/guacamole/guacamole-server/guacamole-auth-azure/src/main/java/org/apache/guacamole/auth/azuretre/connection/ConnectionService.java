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

import java.io.IOException;
import java.net.URI;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ConnectionService {

  /**
   * Logger for this class.
   */
  private static final Logger logger = LoggerFactory.getLogger(ConnectionService.class);

  public Map<String, Connection> getConnections(AzureTREAuthenticatedUser user) throws GuacamoleException {

    Map<String, Connection> connections = new TreeMap<String, Connection>();
    Map<String, GuacamoleConfiguration> configs = this.getConfigurations(user);

    Iterator<Map.Entry<String, GuacamoleConfiguration>> iterator = configs.entrySet().iterator();
    while (iterator.hasNext()) {
      Map.Entry<String, GuacamoleConfiguration> config = iterator.next();
      Connection connection = new TokenInjectingConnection(config.getKey(), config.getKey(), config.getValue(), true,user);
      connection.setParentIdentifier(AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP);
      connections.putIfAbsent(config.getKey(), connection);
    }

    return connections;

  }


  private Map<String, GuacamoleConfiguration> getConfigurations(AzureTREAuthenticatedUser user)
      throws GuacamoleException {

    Map<String, GuacamoleConfiguration> configs = new TreeMap<String, GuacamoleConfiguration>();

    if (user != null) {
      try {

        JSONArray vmsJsonArray = getVMsFromProjectAPI(user);
        URI projectUri = new URI(System.getenv("PROJECT_URL"));

        for (int i = 0; i < vmsJsonArray.length(); i++) {

          GuacamoleConfiguration config = new GuacamoleConfiguration();

          config.setProtocol("RDP");
          JSONObject vmJsonObject = vmsJsonArray.getJSONObject(i);
          config.setProtocol("rdp");

          // Todo: uncomment when both xxxFromProjectAPI calls are implemented
          // https://github.com/microsoft/AzureTRE/issues/558
          // https://github.com/microsoft/AzureTRE/issues/561
          //config.setParameter("hostname", vmJsonObject.get("name").toString() + "." + projectUri.getHost());
          //config.setParameter("username", user.getIdentifier().split("@")[0].toLowerCase());
          // Todo: DELETE when the above is uncommented
          config.setParameter("hostname", System.getenv("TEMP_HOSTNAME"));
          config.setParameter("username", System.getenv("TEMP_USERNAME").toLowerCase());

          config.setParameter("resize-method", "display-update");
          config.setParameter("azure-resource-id", vmJsonObject.get("resourceId").toString());
          config.setParameter("port", "3389");
          config.setParameter("ignore-cert", "true");
          
          config.setParameter("disable-copy", System.getenv("GUAC_DISABLE_COPY"));
          config.setParameter("disable-paste", System.getenv("GUAC_DISABLE_PASTE"));
          config.setParameter("enable-drive", System.getenv("GUAC_ENABLE_DRIVE"));
          config.setParameter("drive-name", System.getenv("GUAC_DRIVE_NAME"));
          config.setParameter("drive-path", System.getenv("GUAC_DRIVE_PATH"));
          config.setParameter("disable-download", System.getenv("GUAC_DISABLE_DOWNLOAD"));


          logger.info("Adding VM: " + config.getParameter("hostname"));
          configs.putIfAbsent(config.getParameter("hostname"), config);

        }
      } catch (Exception e) {
        e.printStackTrace();
        throw new GuacamoleException("Exception getting VMs: " + e.getMessage());

      }
    }

    return configs;

  }

  private JSONArray getVMsFromProjectAPI(AzureTREAuthenticatedUser user) throws GuacamoleException, IOException {

    JSONArray virtualMachines;

    // Todo: Implement / Uncomment when the relevant API call is available for consumption
    // https://github.com/microsoft/AzureTRE/issues/558
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
            .setPath("/api/userserviceinstances").setParameter("ResourceGroupId", System.getenv("RESOURCE_GROUP_ID"))
            .setParameter("ResourceType", "virtual-desktop-guacamole");

        URI uri = uriBuilder.build();
        HttpGet httpget = new HttpGet(uri);
        httpget.addHeader("Authorization", "Bearer " + user.getAccessToken());

        CloseableHttpResponse httpResponse = httpclient.execute(httpget);

        String json = EntityUtils.toString(httpResponse.getEntity());
        if (json.length() != 0) {
          virtualMachines = new JSONArray(json);
        } else {
          virtualMachines = new JSONArray();
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
    return virtualMachines;

     */

    String json = "[ {\"name\": \"1.1.1.1\", \"resourceId\": \"1\"} ]";
    virtualMachines = new JSONArray(json);

    return virtualMachines;
  }

}
