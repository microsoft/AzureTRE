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

package org.apache.guacamole.auth.azuretre.user;

import org.apache.guacamole.net.auth.AbstractAuthenticatedUser;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;

/**
 * Authenticated user implementation that retains TRE-specific context.
 */
public final class AzureTREAuthenticatedUser extends AbstractAuthenticatedUser {

    /** Provider that authenticated the user. */
    private final AuthenticationProvider authProvider;

    /** Credentials originally supplied by the user. */
    private final Credentials credentials;

    /** Azure AD object identifier for the user. */
    private final String objectId;

    /** Access token issued for downstream API calls. */
    private final String accessToken;

    /**
     * Creates a new authenticated user.
     *
     * @param originalCredentials original credentials from the client.
     * @param bearerToken         access token extracted from the headers.
     * @param username            preferred username for the user.
     * @param userObjectId        Azure AD object identifier.
     * @param provider            provider that authenticated the user.
     */
    public AzureTREAuthenticatedUser(
        final Credentials originalCredentials,
        final String bearerToken,
        final String username,
        final String userObjectId,
        final AuthenticationProvider provider) {
        this.credentials = originalCredentials;
        this.accessToken = bearerToken;
        this.objectId = userObjectId;
        this.authProvider = provider;
        setIdentifier(username.toLowerCase());
    }

    @Override
    public AuthenticationProvider getAuthenticationProvider() {
        return authProvider;
    }

    @Override
    public Credentials getCredentials() {
        return credentials;
    }

    /**
     * Returns the bearer token associated with the user.
     *
     * @return the access token string.
     */
    public String getAccessToken() {
        return accessToken;
    }

    /**
     * Returns the Azure AD object identifier associated with the user.
     *
     * @return object identifier value, or {@code null} if unavailable.
     */
    public String getObjectId() {
        return objectId;
    }
}
