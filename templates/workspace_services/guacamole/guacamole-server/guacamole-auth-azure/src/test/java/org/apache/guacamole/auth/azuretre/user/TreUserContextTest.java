package org.apache.guacamole.auth.azuretre.user;
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

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.Directory;
import org.apache.guacamole.net.auth.User;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class TreUserContextTest {

    @Mock
    private AuthenticationProvider authProvider;

    @Mock
    private AzureTREAuthenticatedUser authenticatedUser;

    @Mock
    private Connection mockConnection;

    private Map<String, Connection> connections;

    @BeforeEach
    public void setup() {
        connections = new HashMap<>();
        connections.put("conn1", mockConnection);
    }

    @Test
    public void testTreUserContextCreation() {
        TreUserContext context = new TreUserContext(authProvider, connections);
        assertNotNull(context);
        assertEquals(authProvider, context.getAuthenticationProvider());
    }

    @Test
    public void testInitWithAuthenticatedUser() throws GuacamoleException {
        when(authenticatedUser.getIdentifier()).thenReturn("test-user");

        TreUserContext context = new TreUserContext(authProvider, connections);
        context.init(authenticatedUser);

        User self = context.self();
        assertNotNull(self);
        assertEquals("test-user", self.getIdentifier());
    }

    @Test
    public void testSelfReturnsNullBeforeInit() {
        TreUserContext context = new TreUserContext(authProvider, connections);
        assertNull(context.self());
    }

    @Test
    public void testGetConnectionDirectory() throws GuacamoleException {
        TreUserContext context = new TreUserContext(authProvider, connections);
        context.init(authenticatedUser);

        Directory<Connection> connectionDirectory = context.getConnectionDirectory();
        assertNotNull(connectionDirectory);
        assertTrue(connectionDirectory.getIdentifiers().contains("conn1"));
    }

    @Test
    public void testGetConnectionDirectoryWithEmptyConnections() throws GuacamoleException {
        TreUserContext context = new TreUserContext(authProvider, new HashMap<>());
        context.init(authenticatedUser);

        Directory<Connection> connectionDirectory = context.getConnectionDirectory();
        assertNotNull(connectionDirectory);
        assertTrue(connectionDirectory.getIdentifiers().isEmpty());
    }

    @Test
    public void testSelfHasConnectionPermissions() throws GuacamoleException {
        when(authenticatedUser.getIdentifier()).thenReturn("test-user");

        TreUserContext context = new TreUserContext(authProvider, connections);
        context.init(authenticatedUser);

        User self = context.self();
        assertNotNull(self.getConnectionPermissions());
        assertTrue(self.getConnectionPermissions().hasPermission(
            org.apache.guacamole.net.auth.permission.ObjectPermission.Type.READ, "conn1"));
    }

    @Test
    public void testSelfHasConnectionGroupPermissions() throws GuacamoleException {
        when(authenticatedUser.getIdentifier()).thenReturn("test-user");

        TreUserContext context = new TreUserContext(authProvider, connections);
        context.init(authenticatedUser);

        User self = context.self();
        assertNotNull(self.getConnectionGroupPermissions());
        assertTrue(self.getConnectionGroupPermissions().hasPermission(
            org.apache.guacamole.net.auth.permission.ObjectPermission.Type.READ,
            AzureTREAuthenticationProvider.ROOT_CONNECTION_GROUP));
    }

    @Test
    public void testGetResourceReturnsNull() throws GuacamoleException {
        TreUserContext context = new TreUserContext(authProvider, connections);
        assertNull(context.getResource());
    }

    @Test
    public void testGetAuthenticationProvider() {
        TreUserContext context = new TreUserContext(authProvider, connections);
        assertEquals(authProvider, context.getAuthenticationProvider());
    }

    @Test
    public void testMultipleConnections() throws GuacamoleException {
        connections.put("conn2", mockConnection);
        connections.put("conn3", mockConnection);

        when(authenticatedUser.getIdentifier()).thenReturn("test-user");

        TreUserContext context = new TreUserContext(authProvider, connections);
        context.init(authenticatedUser);

        Directory<Connection> connectionDirectory = context.getConnectionDirectory();
        assertEquals(3, connectionDirectory.getIdentifiers().size());
        assertTrue(connectionDirectory.getIdentifiers().contains("conn1"));
        assertTrue(connectionDirectory.getIdentifiers().contains("conn2"));
        assertTrue(connectionDirectory.getIdentifiers().contains("conn3"));
    }
}
