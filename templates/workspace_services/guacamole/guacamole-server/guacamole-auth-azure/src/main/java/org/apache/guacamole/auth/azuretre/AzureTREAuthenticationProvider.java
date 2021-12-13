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
import com.google.inject.Guice;
import com.google.inject.Injector;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.UserContext;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URL;

public class AzureTREAuthenticationProvider extends AbstractAuthenticationProvider {

    public static final String ROOT_CONNECTION_GROUP = "ROOT";

    /**
     * The standard HTTP parameter which will be included within the URL by all
     * OpenID services upon successful authentication and redirect.
     */
    public static final String PARAMETER_NAME = "id_token";

    private static final Logger LOGGER = LoggerFactory.getLogger(AzureTREAuthenticationProvider.class);

    private final Injector injector;

    public AzureTREAuthenticationProvider() throws GuacamoleException {
        // Set up Guice injector.
        injector = Guice.createInjector(new AzureTREAuthenticationProviderModule(this));
    }

    @Override
    public String getIdentifier() {
        return "azuretre";
    }


    @Override
    public UserContext getUserContext(final AuthenticatedUser authenticatedUser) throws GuacamoleException {
        if (authenticatedUser != null) {
            LOGGER.debug("Got user identifier: " + authenticatedUser.getIdentifier());
            String token = authenticatedUser.getCredentials().getRequest().getParameter(PARAMETER_NAME);

            final AuthenticationProviderService authProviderService;
            authProviderService = injector.getInstance(AuthenticationProviderService.class);

            // Validate the token 'again', the OpenID extension verified it, but it didn't verify
            // that we got the correct roles. The fact that a valid token was returned doesn't mean
            // this user is an Owner or a Researcher. If its not, break, don't try to get any VMs.
            // Note: At the moment there is NO apparent way to UN-Authorize a user that a previous
            // extension authorized... (The user will see an empty list of VMs)
            // Note2: The API app will also verify the token an in any case will not return any vms
            // in this case.
            try {
                final UrlJwkProvider jwkProvider =
                    new UrlJwkProvider(new URL(System.getenv("OPENID_JWKS_ENDPOINT")));
                authProviderService.validateToken(token, jwkProvider);
            }
            catch (final Exception ex) {
                // Failed to validate the token
                LOGGER.error("Failed to validate token. ex: " + ex);
                return null;
            }

            AzureTREAuthenticatedUser treUser = new AzureTREAuthenticatedUser();
            treUser.init(authenticatedUser.getCredentials(), token, authenticatedUser.getIdentifier(), null);
            final UserContext userContext = injector.getInstance(UserContext.class);
            userContext.init(treUser);

            return userContext;
        }
        // Unauthorized
        return null;
    }
}
