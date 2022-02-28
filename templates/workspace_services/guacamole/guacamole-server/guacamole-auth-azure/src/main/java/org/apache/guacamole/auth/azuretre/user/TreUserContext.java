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

import java.util.Map;
import java.util.HashMap;
import java.util.Collections;

import org.apache.guacamole.net.auth.AbstractUserContext;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.User;
import org.apache.guacamole.net.auth.Directory;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.UserGroup;
import org.apache.guacamole.net.auth.simple.SimpleDirectory;

import org.apache.guacamole.GuacamoleException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TreUserContext extends AbstractUserContext {
    private AuthenticationProvider authProvider;

    private Directory<User> userDirectory;
    private Directory<UserGroup> userGroupDirectory;
    private Directory<Connection> connectionDirectory;

    private AadUser self;

    // Logger for this class.
    private static final Logger logger = LoggerFactory.getLogger(TreUserContext.class);

    public TreUserContext(AuthenticationProvider authProvider, TreUser user) throws GuacamoleException {
        logger.info("Creating user context.");

        this.authProvider = authProvider;

        this.self = new AadUser(user.getIdToken());

        Map<String, User> users = new HashMap<>(1);
        users.put(self.getIdentifier(), self);

        this.userDirectory = new SimpleDirectory<>(users);
        this.userGroupDirectory = new SimpleDirectory<>(Collections.emptyMap());
    }

    public void setConnections(Map<String, Connection> connections) throws GuacamoleException
    {
        this.connectionDirectory = new SimpleDirectory<>(connections);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public User self() {

        return this.self;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public AuthenticationProvider getAuthenticationProvider() {

        return this.authProvider;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Directory<Connection> getConnectionDirectory() {
        return this.connectionDirectory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Directory<User> getUserDirectory() {
        return this.userDirectory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Directory<UserGroup> getUserGroupDirectory() {
        return this.userGroupDirectory;
    }
}
