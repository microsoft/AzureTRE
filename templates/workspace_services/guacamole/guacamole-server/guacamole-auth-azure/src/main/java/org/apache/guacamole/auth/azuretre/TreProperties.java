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

import java.net.URI;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.environment.Environment;
import org.apache.guacamole.environment.LocalEnvironment;
import org.apache.guacamole.properties.StringGuacamoleProperty;
import org.apache.guacamole.properties.URIGuacamoleProperty;

public class TreProperties {
    /**
     * The Guacamole server environment.
     */
    private final Environment environment;

    public TreProperties() throws GuacamoleException {
        environment = new LocalEnvironment();
    }

    private static final StringGuacamoleProperty SCOPE = new StringGuacamoleProperty() {
        @Override
        public String getName() {
            return "azuread-scope";
        }
    };

    private static final URIGuacamoleProperty AUTHORITY = new URIGuacamoleProperty() {
        @Override
        public String getName() {
            return "azuread-authority";
        }
    };

    private static final StringGuacamoleProperty CLIENT_SECRET = new StringGuacamoleProperty() {
        @Override
        public String getName() {
            return "azuread-client-secret";
        }
    };

    private static final StringGuacamoleProperty CLIENT_ID = new StringGuacamoleProperty() {
        @Override
        public String getName() {
            return "azuread-client-id";
        }
    };

    private static final URIGuacamoleProperty REDIRECT_URL = new URIGuacamoleProperty() {
        @Override
        public String getName() {
            return "azuread-redirect-url";
        }
    };

    private static final URIGuacamoleProperty API_URL = new URIGuacamoleProperty() {
        @Override
        public String getName() {
            return "api-url";
        }
    };

    public String getClientId() throws GuacamoleException {
        return environment.getRequiredProperty(CLIENT_ID);
    }

    public String getClientSecret() throws GuacamoleException {
        return environment.getRequiredProperty(CLIENT_SECRET);
    }

    public String getScope() throws GuacamoleException {
        return environment.getRequiredProperty(SCOPE);
    }

    public URI getAuthority() throws GuacamoleException {
        return environment.getRequiredProperty(AUTHORITY);
    }

    public URI getRedirectUri() throws GuacamoleException {
        return environment.getRequiredProperty(REDIRECT_URL);
    }

    public URI getAPIUri() throws GuacamoleException {
        return environment.getRequiredProperty(API_URL);
    }
}

