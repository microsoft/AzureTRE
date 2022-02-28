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
package org.apache.guacamole.auth.azuretre;

import com.microsoft.aad.msal4j.IConfidentialClientApplication;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.connection.ConnectionService;
import org.apache.guacamole.auth.azuretre.user.TreUser;
import org.apache.guacamole.auth.azuretre.user.TreUserContext;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Credentials;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

public class TreAuthenticationProvider extends AbstractAuthenticationProvider {

    private static final Logger logger = LoggerFactory.getLogger(TreAuthenticationProvider.class);
    public static final String ROOT_CONNECTION_GROUP = "ROOT";

    private final AuthenticationProviderService service;

    public TreAuthenticationProvider() throws GuacamoleException {

        logger.info("Creating TRE Authentication Provider");

        service = new AuthenticationProviderService(this);
    }

    @Override
    public String getIdentifier() {
        return "azuretre";
    }

    @Override
    public TreUser authenticateUser(Credentials credentials) throws GuacamoleException {
        return service.authenticateUser(credentials);
    }

    @Override
    public TreUserContext getUserContext(AuthenticatedUser authenticatedUser) throws GuacamoleException {
        if (authenticatedUser instanceof TreUser) {
            logger.info("Getting user context.");
            TreUser user = (TreUser) authenticatedUser;

            try (ConnectionService connectionService = new ConnectionService(user)) {
                TreUserContext treUserContext = new TreUserContext(this, user);

                treUserContext.setConnections(connectionService.getConnections(user));

                return treUserContext;
            } catch (IOException e) {
                logger.error(e.getMessage(), e);
                throw new GuacamoleException(e);
            }
        }
        return null;
    }

    public IConfidentialClientApplication getAppClient() throws GuacamoleException {
        return service.getConfidentialClientInstance();
    }
}
