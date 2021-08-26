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

import com.auth0.jwk.Jwk;
import com.auth0.jwk.UrlJwkProvider;
import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.interfaces.Claim;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.google.inject.Inject;
import com.google.inject.Provider;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.servlet.http.HttpServletRequest;
import java.net.MalformedURLException;
import java.net.URL;
import java.security.interfaces.RSAPublicKey;

public class AuthenticationProviderService {

    private static final Logger LOGGER = LoggerFactory.getLogger(AzureTREAuthenticationProvider.class);

    @Inject
    private Provider<AzureTREAuthenticatedUser> authenticatedUserProvider;

    public AzureTREAuthenticatedUser authenticateUser(final Credentials credentials) throws GuacamoleException {
        LOGGER.info("authenticateUser");
        // Pull HTTP header from request if present
        final HttpServletRequest request = credentials.getRequest();
        // Get the username from the header
        final String accessToken = request.getHeader("x-Access-Token");
        LOGGER.info("### access token {}", accessToken);
        if (accessToken != null) {
            final AzureTREAuthenticatedUser authenticatedUser = authenticatedUserProvider.get();
            try {
                final UrlJwkProvider jwkProvider = new UrlJwkProvider(new URL(
                    "https://login.microsoftonline.com/" + System.getenv("TENANT_ID") + "/discovery/v2.0/keys"));
                validateToken(credentials, accessToken, authenticatedUser, jwkProvider);

                return authenticatedUser;
            } catch (final MalformedURLException ex) {
                LOGGER.error("Could not parse JWK Provider URL ", ex);
                throw new GuacamoleException("Could not parse JWK Provider URL");
            }
        }

        // Authentication not provided via header, yet, so we request it.
        throw new GuacamoleInvalidCredentialsException("Invalid login.", CredentialsInfo.USERNAME_PASSWORD);
    }

    private void validateToken(final Credentials credentials, final String accessToken,
                               final AzureTREAuthenticatedUser authenticatedUser,
                               final UrlJwkProvider jwkProvider) throws GuacamoleInvalidCredentialsException {
        try {
            if (System.getenv("AUDIENCE").length() == 0) {
                throw new Exception("AUDIENCE is not provided");
            }
            if (System.getenv("ISSUER").length() == 0) {
                throw new Exception("ISSUER is not provided");
            }
            final Jwk jwk = jwkProvider.get(JWT.decode(accessToken).getKeyId());
            final Algorithm algorithm = Algorithm.RSA256((RSAPublicKey) jwk.getPublicKey(), null);
            final JWTVerifier verifier = JWT.require(algorithm)
                .withAudience(System.getenv("AUDIENCE"))
                .withClaimPresence("roles")
                .withIssuer(System.getenv("ISSUER"))
                .build();

            final DecodedJWT jwt = verifier.verify(accessToken);
            // Since we verify we have the correct Audience we validate the token if at least one role is present, no
            // matter which one.
            final Claim roles = jwt.getClaim("roles");
            if (roles == null || roles.isNull() || roles.asArray(Object.class).length == 0) {
                throw new GuacamoleInvalidCredentialsException(
                    "Token must contain a 'roles' claim", CredentialsInfo.USERNAME_PASSWORD);
            }
            final String objectId = jwt.getClaim("oid").asString();
            final String username = jwt.getClaim("preferred_username").asString();

            authenticatedUser.init(credentials, accessToken, username, objectId);
        } catch (final Exception ex) {
            LOGGER.error("Could not initialise user, possible access token verification issue: ", ex);
            throw new GuacamoleInvalidCredentialsException(
                "Could not initialise user, possible access token verification issue:" + ex.getMessage(),
                CredentialsInfo.USERNAME_PASSWORD);
        }
    }
}
