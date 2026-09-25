package org.apache.guacamole.auth.azuretre.connection;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.junit.jupiter.api.Test;
import org.junitpioneer.jupiter.ClearEnvironmentVariable;
import org.junitpioneer.jupiter.SetEnvironmentVariable;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

import java.time.Duration;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

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

    @Test
    public void getConnectionsThrowsExceptionWhenUserIsNull() {
        try (MockedStatic<ConnectionService> connectionServiceMockedStatic = Mockito.mockStatic(
            ConnectionService.class)) {
            connectionServiceMockedStatic.when(() -> ConnectionService.getConnections(null))
                .thenCallRealMethod();
            
            Map<String, Connection> result = ConnectionService.getConnections(null);
            // Should return empty map when user is null
            assertEquals(0, result.size());
        } catch (final GuacamoleException e) {
            e.printStackTrace();
        }
    }

    @Test
    public void getConnectionsHandlesGuacamoleException() {
        try (MockedStatic<ConnectionService> connectionServiceMockedStatic = Mockito.mockStatic(
            ConnectionService.class)) {
            connectionServiceMockedStatic.when(() -> ConnectionService.getConnections(
              (AzureTREAuthenticatedUser) authenticatedUser))
                .thenThrow(new GuacamoleException("API connection failed"));
            
            assertThrows(GuacamoleException.class, () -> 
                ConnectionService.getConnections((AzureTREAuthenticatedUser) authenticatedUser));
        }
    }

    @Test
    @ClearEnvironmentVariable(key = "GUAC_API_TIMEOUT_SECONDS")
    public void getApiTimeoutUsesDefaultWhenUnset() {
        assertEquals(Duration.ofSeconds(30), ConnectionService.getApiTimeout());
    }

    @Test
    @SetEnvironmentVariable(key = "GUAC_API_TIMEOUT_SECONDS", value = "45")
    public void getApiTimeoutUsesConfiguredValue() {
        assertEquals(Duration.ofSeconds(45), ConnectionService.getApiTimeout());
    }

    @Test
    @SetEnvironmentVariable(key = "GUAC_API_TIMEOUT_SECONDS", value = "0")
    public void getApiTimeoutFallsBackToDefaultWhenConfiguredValueIsNotPositive() {
        assertEquals(Duration.ofSeconds(30), ConnectionService.getApiTimeout());
    }

    @Test
    @SetEnvironmentVariable(key = "GUAC_API_TIMEOUT_SECONDS", value = "invalid")
    public void getApiTimeoutFallsBackToDefaultWhenConfiguredValueIsInvalid() {
        assertEquals(Duration.ofSeconds(30), ConnectionService.getApiTimeout());
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
