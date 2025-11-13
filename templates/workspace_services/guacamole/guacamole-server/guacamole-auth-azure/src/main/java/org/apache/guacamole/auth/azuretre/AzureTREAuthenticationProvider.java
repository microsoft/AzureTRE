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
import org.apache.guacamole.auth.azuretre.connection.ConnectionService;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.TreUserContext;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.UserContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.MalformedURLException;
import java.net.URL;
import java.util.Map;

/**
 * Authentication provider that integrates Guacamole with Azure TRE.
 */
public final class AzureTREAuthenticationProvider
    extends AbstractAuthenticationProvider {

    /** Root connection group identifier. */
    public static final String ROOT_CONNECTION_GROUP = "ROOT";

    /** Logger for provider actions. */
    private static final Logger LOGGER = LoggerFactory.getLogger(
        AzureTREAuthenticationProvider.class);

    /** Service responsible for token validation. */
    private final AuthenticationProviderService authenticationProviderService;

    /**
     * Creates a provider with a default authentication service.
     */
    public AzureTREAuthenticationProvider() {
        this.authenticationProviderService =
            new AuthenticationProviderService();
    }

    /**
     * Creates a provider with the given authentication service.
     *
     * @param providerService optional service override.
     */
    public AzureTREAuthenticationProvider(
        final AuthenticationProviderService providerService) {
        if (providerService == null) {
            this.authenticationProviderService =
                new AuthenticationProviderService();
        } else {
            this.authenticationProviderService = providerService;
        }
    }

    @Override
    public String getIdentifier() {
        return "azuretre";
    }

    @Override
    public AuthenticatedUser updateAuthenticatedUser(
        final AuthenticatedUser authenticatedUser,
        final Credentials credentials) throws GuacamoleException {
        return authenticateUser(credentials);
    }

    @Override
    public AzureTREAuthenticatedUser authenticateUser(
        final Credentials credentials) {
        final var requestDetails = credentials.getRequestDetails();
        final String accessToken = requestDetails.getHeader(
            "X-Forwarded-Access-Token");
        final String prefUsername = requestDetails.getHeader(
            "X-Forwarded-Preferred-Username");

        if (Strings.isNullOrEmpty(accessToken)) {
            LOGGER.error("Access token was not provided");
            return null;
        }
        if (Strings.isNullOrEmpty(prefUsername)) {
            LOGGER.error("Preferred username missing from headers");
            return null;
        }

        return new AzureTREAuthenticatedUser(
            credentials,
            accessToken,
            prefUsername,
            null,
            this);
    }

    @Override
    public UserContext getUserContext(
        final AuthenticatedUser authenticatedUser)
        throws GuacamoleException {
        if (!(authenticatedUser instanceof AzureTREAuthenticatedUser)) {
            return null;
        }

        final AzureTREAuthenticatedUser user =
            (AzureTREAuthenticatedUser) authenticatedUser;
        final String accessToken = user.getAccessToken();

        try {
            LOGGER.info("Validating token");
            final UrlJwkProvider jwkProvider = new UrlJwkProvider(
                buildJwksEndpointUrl());
            authenticationProviderService.validateToken(
                accessToken,
                jwkProvider);
        } catch (final Exception ex) {
            LOGGER.error("Failed to validate token: {}", ex.getMessage());
            LOGGER.debug("Token validation failure", ex);
            return null;
        }

        final Map<String, Connection> connections =
            ConnectionService.getConnections(user);
        final TreUserContext treUserContext = new TreUserContext(
            this,
            connections);
        treUserContext.init(user);
        return treUserContext;
    }

    @Override
    public UserContext updateUserContext(
        final UserContext context,
        final AuthenticatedUser authenticatedUser,
        final Credentials credentials) throws GuacamoleException {
        return getUserContext(authenticatedUser);
    }

    private URL buildJwksEndpointUrl() throws MalformedURLException {
        return new URL(System.getenv("OAUTH2_PROXY_JWKS_ENDPOINT"));
    }
}
