package org.apache.guacamole.auth.azuretre.connection;
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

import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

@ExtendWith(MockitoExtension.class)
public class TokenInjectingConnectionTest {

    private GuacamoleConfiguration config;
    private TokenInjectingConnection connection;

    @BeforeEach
    public void setup() {
        config = new GuacamoleConfiguration();
        config.setProtocol("rdp");
        config.setParameter("hostname", "10.0.0.1");
        config.setParameter("display_name", "Test VM");
        config.setParameter("azure-resource-id", "test-resource-id");
    }

    @Test
    public void testTokenInjectingConnectionCreation() {
        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, true);

        assertNotNull(connection);
        assertEquals("Test Connection", connection.getName());
        assertEquals("conn-id", connection.getIdentifier());
        assertEquals(config, connection.getConfiguration());
    }

    @Test
    public void testTokenInjectingConnectionWithInterpretTokensFalse() {
        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, false);

        assertNotNull(connection);
        assertEquals("Test Connection", connection.getName());
    }

    @Test
    public void testGetConfiguration() {
        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, true);

        GuacamoleConfiguration retrievedConfig = connection.getConfiguration();
        assertNotNull(retrievedConfig);
        assertEquals("rdp", retrievedConfig.getProtocol());
        assertEquals("10.0.0.1", retrievedConfig.getParameter("hostname"));
        assertEquals("Test VM", retrievedConfig.getParameter("display_name"));
    }

    @Test
    public void testGetName() {
        connection = new TokenInjectingConnection("My Test VM", "conn-id", config, true);
        assertEquals("My Test VM", connection.getName());
    }

    @Test
    public void testGetIdentifier() {
        connection = new TokenInjectingConnection("Test Connection", "unique-id-123", config, true);
        assertEquals("unique-id-123", connection.getIdentifier());
    }

    @Test
    public void testSetAndGetParentIdentifier() {
        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, true);
        connection.setParentIdentifier("ROOT");
        assertEquals("ROOT", connection.getParentIdentifier());
    }

    @Test
    public void testConfigurationWithAzureResourceId() {
        config.setParameter("azure-resource-id", "resource-123");
        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, true);

        assertEquals("resource-123", connection.getConfiguration().getParameter("azure-resource-id"));
    }

    @Test
    public void testMultipleConfigurationParameters() {
        config.setParameter("port", "3389");
        config.setParameter("ignore-cert", "true");
        config.setParameter("resize-method", "display-update");

        connection = new TokenInjectingConnection("Test Connection", "conn-id", config, true);

        GuacamoleConfiguration retrievedConfig = connection.getConfiguration();
        assertEquals("3389", retrievedConfig.getParameter("port"));
        assertEquals("true", retrievedConfig.getParameter("ignore-cert"));
        assertEquals("display-update", retrievedConfig.getParameter("resize-method"));
    }

    @Test
    public void testConnectionWithNullName() {
        connection = new TokenInjectingConnection(null, "conn-id", config, true);
        assertNull(connection.getName());
        assertEquals("conn-id", connection.getIdentifier());
    }

    @Test
    public void testConnectionWithEmptyName() {
        connection = new TokenInjectingConnection("", "conn-id", config, true);
        assertEquals("", connection.getName());
    }

    @Test
    public void testConnectionWithMinimalConfiguration() {
        GuacamoleConfiguration minimalConfig = new GuacamoleConfiguration();
        minimalConfig.setProtocol("rdp");

        connection = new TokenInjectingConnection("Minimal", "min-id", minimalConfig, true);
        assertNotNull(connection);
        assertEquals("rdp", connection.getConfiguration().getProtocol());
    }
}
