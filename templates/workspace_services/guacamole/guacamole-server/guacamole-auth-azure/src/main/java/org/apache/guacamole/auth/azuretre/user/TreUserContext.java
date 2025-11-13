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

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.net.auth.AbstractUserContext;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.Directory;
import org.apache.guacamole.net.auth.User;
import org.apache.guacamole.net.auth.permission.ObjectPermissionSet;
import org.apache.guacamole.net.auth.simple.SimpleDirectory;
import org.apache.guacamole.net.auth.simple.SimpleObjectPermissionSet;
import org.apache.guacamole.net.auth.simple.SimpleUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.Map;

/**
 * User context that exposes TRE connections to authenticated users.
 */
public final class TreUserContext extends AbstractUserContext {

    /** Logger for lifecycle events. */
    private static final Logger LOGGER = LoggerFactory.getLogger(
        TreUserContext.class);

    /** Backing authentication provider. */
    private final AuthenticationProvider authProvider;

    /** Directory containing connections available to the user. */
    private final Directory<Connection> connectionDirectory;

    /** Representation of the authenticated user. */
    private User self;

    /**
     * Creates a new user context with the supplied connection directory.
     *
     * @param provider   backing authentication provider.
     * @param connectionMap  available connection map.
     */
    public TreUserContext(
        final AuthenticationProvider provider,
        final Map<String, Connection> connectionMap) {
        LOGGER.debug("Creating a new TRE user context");
        this.authProvider = provider;
        this.connectionDirectory = new SimpleDirectory<>(connectionMap);
    }

    /**
     * Initialises the context for the supplied authenticated user.
     *
     * @param user authenticated TRE user.
     * @throws GuacamoleException if permission calculations fail.
     */
    public void init(final AzureTREAuthenticatedUser user)
        throws GuacamoleException {
        self = new SimpleUser(user.getIdentifier()) {

            @Override
            public ObjectPermissionSet getConnectionPermissions()
                throws GuacamoleException {
                return new SimpleObjectPermissionSet(
                    connectionDirectory.getIdentifiers());
            }

            @Override
            public ObjectPermissionSet getConnectionGroupPermissions() {
                return new SimpleObjectPermissionSet(Collections.singleton(
                    AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP));
            }
        };
    }

    @Override
    public User self() {
        return self;
    }

    @Override
    public AuthenticationProvider getAuthenticationProvider() {
        LOGGER.debug("getAuthenticationProvider");
        return authProvider;
    }

    /**
     * Returns the directory containing the user's connections.
     *
     * @return directory of connections.
     */
    public Directory<Connection> getConnectionDirectory() {
        LOGGER.debug("getConnectionDirectory");
        return connectionDirectory;
    }
}
