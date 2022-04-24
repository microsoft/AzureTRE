package org.apache.guacamole.auth.azuretre.connection;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ConnectionServiceTest {
    @Mock
    AuthenticatedUser authenticatedUser;

    @Test
    public void getConnectionsWhenEmpty() {
        final Map<String, Connection> connectionList = Collections.emptyMap();
        testGetConnections(connectionList);
    }

    @Test
    public void getConnectionsWhenMany() {
        final Map<String, Connection> connectionList  = new HashMap<>() {{
                put("dummy_connection", null);
            }};
        testGetConnections(connectionList);
    }

    private void testGetConnections(final Map<String, Connection> connectionList) {
        try (MockedStatic<ConnectionService> connectionServiceMockedStatic = Mockito.mockStatic(
            ConnectionService.class)) {
            connectionServiceMockedStatic.when(() -> ConnectionService.getConnections(
              (AzureTREAuthenticatedUser) authenticatedUser))
                .thenReturn(connectionList);
            assertEquals(connectionList, ConnectionService.getConnections(
                (AzureTREAuthenticatedUser) authenticatedUser));
        } catch (final GuacamoleException e) {
            e.printStackTrace();
        }
    }
}
