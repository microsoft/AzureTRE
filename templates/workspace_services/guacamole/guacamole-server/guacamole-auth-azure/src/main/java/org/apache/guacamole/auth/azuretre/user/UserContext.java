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


import com.google.inject.Inject;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.net.auth.AbstractUserContext;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.ConnectionGroup;
import org.apache.guacamole.net.auth.Directory;
import org.apache.guacamole.net.auth.User;
import org.apache.guacamole.net.auth.simple.SimpleUser;
import org.apache.guacamole.net.auth.simple.SimpleDirectory;
import org.apache.guacamole.net.auth.simple.SimpleConnectionGroup;
import org.apache.guacamole.auth.azuretre.connection.ConnectionService;
import org.apache.guacamole.net.auth.UserGroup;
import org.apache.guacamole.net.auth.simple.SimpleObjectPermissionSet;
import org.apache.guacamole.net.auth.permission.ObjectPermissionSet;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class UserContext extends AbstractUserContext {

    private static final Logger logger = LoggerFactory.getLogger(UserContext.class);

    @Inject
    private ConnectionService connectionService;

    @Inject
    private AuthenticationProvider authProvider;
 
  
    private User self;

    private Directory<User> userDirectory;

    private Directory<UserGroup> userGroupDirectory;

    private Directory<Connection> connectionDirectory;

    private ConnectionGroup rootGroup;

 
    public void init(AzureTREAuthenticatedUser user)
            throws GuacamoleException {
        
        Map<String, User> users = new HashMap<>(1);
        users.put(user.getIdentifier(),new SimpleUser(user.getIdentifier()));
        
        userDirectory = new SimpleDirectory<>(
            users
        );

        // Query all accessible user groups
        userGroupDirectory = new SimpleDirectory<>(
            Collections.emptyMap()
        );

        // Query all accessible connections
        connectionDirectory = new SimpleDirectory<>(        
            connectionService.getConnections(user)
        );

        // Root group contains only connections
        rootGroup = new SimpleConnectionGroup(
            AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP,
            AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP,
            connectionDirectory.getIdentifiers(),
            Collections.<String>emptyList()
        );

        self = new SimpleUser(user.getIdentifier()){

            @Override
            public ObjectPermissionSet getUserPermissions() throws GuacamoleException {
                return new SimpleObjectPermissionSet(userDirectory.getIdentifiers());
            }

            @Override
            public ObjectPermissionSet getUserGroupPermissions() throws GuacamoleException {
                return new SimpleObjectPermissionSet(userGroupDirectory.getIdentifiers());
            }

            @Override
            public ObjectPermissionSet getConnectionPermissions() throws GuacamoleException {
                return new SimpleObjectPermissionSet(connectionDirectory.getIdentifiers());
            }

            @Override
            public ObjectPermissionSet getConnectionGroupPermissions() throws GuacamoleException {
                return new SimpleObjectPermissionSet(Collections.singleton(AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP));
            }

        };
    }

    @Override
    public User self() {
        return self;
    }

    @Override
    public AuthenticationProvider getAuthenticationProvider() {
        logger.debug("getAuthenticationProvider");
        return authProvider;
    }

    @Override
    public Directory<User> getUserDirectory() throws GuacamoleException {
        
        logger.debug("getUserDirectory");
        return userDirectory;
    }

    @Override
    public Directory<UserGroup> getUserGroupDirectory() throws GuacamoleException {
        logger.debug("getUserGroupDirectory");
        return userGroupDirectory;
    }

    @Override
    public Directory<Connection> getConnectionDirectory() throws GuacamoleException {
        logger.debug("getConnectionDirectory");
        return connectionDirectory;
    }

    @Override
    public ConnectionGroup getRootConnectionGroup() throws GuacamoleException {
        logger.debug("getRootConnectionGroup");
        return rootGroup;
    }

}
