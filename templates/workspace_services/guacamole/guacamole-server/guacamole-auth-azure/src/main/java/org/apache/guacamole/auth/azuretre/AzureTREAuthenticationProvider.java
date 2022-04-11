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

import com.auth0.jwk.UrlJwkProvider;
import com.google.common.base.Strings;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.UserContext;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Credentials;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URL;

public class AzureTREAuthenticationProvider extends AbstractAuthenticationProvider {

    public static final String ROOT_CONNECTION_GROUP = "ROOT";

    private static final Logger LOGGER = LoggerFactory.getLogger(AzureTREAuthenticationProvider.class);

    public AzureTREAuthenticationProvider() {
    }

    @Override
    public String getIdentifier() {
        return "azuretre";
    }

    @Override
    public AzureTREAuthenticatedUser authenticateUser(final Credentials credentials) {
        LOGGER.info("Authenticating user");

        // Getting headers from the oauth2 proxy
        final String accessToken = credentials.getRequest().getHeader("X-Forwarded-Access-Token");
        final String prefEmail = credentials.getRequest().getHeader("X-Forwarded-Email");


        if (Strings.isNullOrEmpty(accessToken)) {
            LOGGER.error("access token was not provided");
            return null;
        }
        if (Strings.isNullOrEmpty(prefEmail)) {
            LOGGER.error("email was not provided");
            return null;
        }

        final AzureTREAuthenticatedUser treUser = new AzureTREAuthenticatedUser();
        treUser.init(credentials, accessToken, prefEmail, null, this);
        return treUser;
    }

    @Override
    public UserContext getUserContext(final AuthenticatedUser authenticatedUser) throws GuacamoleException {
        LOGGER.debug("Getting user context.");

        if (authenticatedUser instanceof AzureTREAuthenticatedUser) {
            final AzureTREAuthenticatedUser user = (AzureTREAuthenticatedUser) authenticatedUser;
            final String accessToken = user.getAccessToken();

            final AuthenticationProviderService authProviderService = new AuthenticationProviderService();

          final UserContext treUserContext = new UserContext(this);
            treUserContext.init(user);

            // Validate the token 'again', the OpenID extension verified it, but it didn't verify
            // that we got the correct roles. The fact that a valid token was returned doesn't mean
            // this user is an Owner or a Researcher. If its not, break, don't try to get any VMs.
            // Note: At the moment there is NO apparent way to UN-Authorize a user that a previous
            // extension authorized... (The user will see an empty list of VMs)
            // Note2: The API app will also verify the token an in any case will not return any vms
            // in this case.
            try {
                LOGGER.info("Validating token");
                final UrlJwkProvider jwkProvider =
                    new UrlJwkProvider(new URL(System.getenv("OAUTH2_PROXY_JWKS_ENDPOINT")));
                authProviderService.validateToken(accessToken, jwkProvider);
            }
            catch (final Exception ex) {
                // Failed to validate the token
                LOGGER.error("Failed to validate token. ex: " + ex);
                return null;
            }

            return treUserContext;
        }
        return null;
    }
}
