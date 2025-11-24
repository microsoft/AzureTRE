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
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.security.interfaces.RSAPublicKey;
import java.util.List;

/**
 * Service responsible for validating access tokens issued to TRE users.
 */
public final class AuthenticationProviderService {

    /** Logger for validation errors. */
    private static final Logger LOGGER = LoggerFactory.getLogger(
        AzureTREAuthenticationProvider.class);

    /**
     * Validates the supplied JWT token using the provided JWK provider.
     *
     * @param token        access token presented by the client.
     * @param jwkProvider  provider used to resolve signing keys.
     * @throws GuacamoleInvalidCredentialsException if validation fails.
     */
    public void validateToken(
        final String token,
        final UrlJwkProvider jwkProvider)
        throws GuacamoleInvalidCredentialsException {
        try {
            if (System.getenv("AUDIENCE").length() == 0) {
                throw new Exception("AUDIENCE is not provided");
            }
            if (System.getenv("ISSUER").length() == 0) {
                throw new Exception("ISSUER is not provided");
            }

            final Jwk jwk = jwkProvider.get(JWT.decode(token).getKeyId());
            final Algorithm algorithm = Algorithm.RSA256(
                (RSAPublicKey) jwk.getPublicKey(),
                null);
            final JWTVerifier verifier = JWT.require(algorithm)
                .withAudience(System.getenv("AUDIENCE"))
                .withClaimPresence("roles")
                .withIssuer(System.getenv("ISSUER"))
                .build();

            final DecodedJWT jwt = verifier.verify(token);
            final Claim roles = jwt.getClaim("roles");
            if (roles == null
                || roles.isNull()
                || roles.asArray(Object.class).length == 0) {
                throw new GuacamoleInvalidCredentialsException(
                    "Token must contain a 'roles' claim",
                    CredentialsInfo.USERNAME_PASSWORD);
            }

            final List<String> rolesList = roles.asList(String.class);
            final boolean hasAuthorisedRole = rolesList.stream().anyMatch(
                role -> role.equalsIgnoreCase("WorkspaceOwner")
                    || role.equalsIgnoreCase("WorkspaceResearcher")
                    || role.equalsIgnoreCase("AirlockManager"));
            if (!hasAuthorisedRole) {
                throw new GuacamoleInvalidCredentialsException(
                    "User must have workspace owner, workspace researcher, "
                        + "or Airlock Manager role",
                    CredentialsInfo.USERNAME_PASSWORD);
            }
        } catch (final GuacamoleInvalidCredentialsException ex) {
            // Re-throw without logging to avoid leaking role information.
            throw ex;
        } catch (final com.auth0.jwt.exceptions.JWTVerificationException ex) {
            LOGGER.error("JWT verification failed: {}", ex.getMessage());
            throw new GuacamoleInvalidCredentialsException(
                ex.getMessage(),
                CredentialsInfo.USERNAME_PASSWORD);
        } catch (final Exception ex) {
            LOGGER.error(
                "Token validation failed: {}",
                ex.getClass().getSimpleName());
            LOGGER.debug("Detailed validation error", ex);
            throw new GuacamoleInvalidCredentialsException(
                "Token validation failed",
                CredentialsInfo.USERNAME_PASSWORD);
        }
    }
}
