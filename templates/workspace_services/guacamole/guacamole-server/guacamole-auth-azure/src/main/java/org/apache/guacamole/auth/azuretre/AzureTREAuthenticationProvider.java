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

import com.google.inject.Guice;
import com.google.inject.Injector;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.UserContext;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.net.auth.Credentials;



public class AzureTREAuthenticationProvider extends AbstractAuthenticationProvider {

    public static final String ROOT_CONNECTION_GROUP = "ROOT";

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
    public AzureTREAuthenticatedUser authenticateUser(Credentials credentials)
            throws GuacamoleException {

        // Pass credentials to authentication service.
        AuthenticationProviderService authProviderService = injector.getInstance(AuthenticationProviderService.class);
        return authProviderService.authenticateUser(credentials);

    }

    @Override
    public UserContext getUserContext(AuthenticatedUser authenticatedUser) throws GuacamoleException {


        if (authenticatedUser != null) {

            UserContext userContext = injector.getInstance(UserContext.class);

            if (authenticatedUser instanceof AzureTREAuthenticatedUser)
                userContext.init((AzureTREAuthenticatedUser) authenticatedUser);
                
            return userContext;
        }

        // Unauthorized
        return null;

    }
    
}
