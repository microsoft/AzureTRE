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

import java.net.MalformedURLException;
import java.text.ParseException;
import java.util.Set;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import com.microsoft.aad.msal4j.IAccount;
import com.microsoft.aad.msal4j.IAuthenticationResult;
import com.microsoft.aad.msal4j.IConfidentialClientApplication;
import com.microsoft.aad.msal4j.ITokenCache;
import com.microsoft.aad.msal4j.SilentParameters;

import com.nimbusds.jwt.JWT;
import com.nimbusds.jwt.JWTParser;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.TreAuthenticationProvider;
import org.apache.guacamole.net.auth.AbstractAuthenticatedUser;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;

public class TreUser extends AbstractAuthenticatedUser {

    private final TreAuthenticationProvider authenticationProvider;
    private final Credentials credentials;
    private final IAccount account;
    private final JWT idToken;
    private String tokenCacheJson;

    public TreUser(TreAuthenticationProvider authenticationProvider, Credentials credentials,
                   IAuthenticationResult authResult, ITokenCache tokenCache) throws GuacamoleException {
        this.authenticationProvider = authenticationProvider;
        this.credentials = credentials;
        this.account = authResult.account();
        storeTokenCache(tokenCache);
        try {
            this.idToken = JWTParser.parse(authResult.idToken());
            String name = this.idToken.getJWTClaimsSet().getStringClaim("name");
            setIdentifier(name);
        } catch (ParseException e) {
            throw new GuacamoleInvalidCredentialsException("Error parsing the id_token", CredentialsInfo.EMPTY);
        }
    }

    @Override
    public AuthenticationProvider getAuthenticationProvider() {
        return this.authenticationProvider;
    }

    @Override
    public Credentials getCredentials() {
        return this.credentials;
    }

    @Override
    public void invalidate() {
    }

    public IAccount account() {
        return this.account;
    }

    public JWT getIdToken() {
        return this.idToken;
    }

    public String getTokenCache() {
        return this.tokenCacheJson;
    }

    public void storeTokenCache(ITokenCache tokenCache) {
        tokenCacheJson = tokenCache.serialize();
    }

    /**
     * Uses the token cache to get an access token (for the specified scopes).
     * If the cached token has expired, the refresh token to used to get a new
     * one from Azure AD.
     *
     * @param scopes The required scopes.
     * @return The API access token that can be used as a bearer token in API
     *         calls, or null if the token cannot be acquired.
     */
    public String getToken(Set<String> scopes) {

        final SilentParameters parameters = SilentParameters.builder(scopes, this.account()).build();

        try {
            final IConfidentialClientApplication client = this.authenticationProvider.getAppClient();
            client.tokenCache().deserialize(this.getTokenCache());

            final CompletableFuture<IAuthenticationResult> future = client.acquireTokenSilently(parameters);
            final IAuthenticationResult result = future.get();

            if (result != null) {
                this.storeTokenCache(client.tokenCache());
                return result.accessToken();
            }

            return null;
        } catch (final MalformedURLException ex) {
            return null;
        } catch (ExecutionException | CancellationException | InterruptedException ex) {
            return null;
        } catch (GuacamoleException ex) {
            return null;
        }
    }
}
