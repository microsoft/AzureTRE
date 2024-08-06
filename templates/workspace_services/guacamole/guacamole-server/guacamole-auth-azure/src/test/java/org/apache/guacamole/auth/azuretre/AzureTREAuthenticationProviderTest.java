package org.apache.guacamole.auth.azuretre;

import com.auth0.jwk.UrlJwkProvider;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.connection.ConnectionService;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.auth.azuretre.user.TreUserContext;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.Connection;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junitpioneer.jupiter.SetEnvironmentVariable;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import javax.servlet.http.HttpServletRequest;

import java.util.HashMap;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)

public class AzureTREAuthenticationProviderTest {
    public static final String OAUTH_2_PROXY_JWKS_ENDPOINT = "OAUTH2_PROXY_JWKS_ENDPOINT";
    public static final String JWKS_MOCK_ENDPOINT_URL = "https://mockedjwks.com";
    public static final String MOCKED_TOKEN = "dummy_token";
    public static final String MOCKED_USERNAME = "mocked@mail.com";
    @Mock
    AuthenticationProviderService authenticationProviderService;
    @Mock
    HttpServletRequest requestMock;
    @InjectMocks
    Credentials credentialsMock;
    AzureTREAuthenticationProvider azureTREAuthenticationProvider;
    @Mock
    AzureTREAuthenticatedUser authenticatedUser;


    @BeforeEach
    void setup() {
        azureTREAuthenticationProvider = new AzureTREAuthenticationProvider(authenticationProviderService);
    }

    @Test
    public void authenticateUserSucceed() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn(MOCKED_TOKEN);
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Preferred-Username")).thenReturn(MOCKED_USERNAME);

        assertNotNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }

    @Test
    public void authenticateUserFailsWhenNoAccessToken() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn("");
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Preferred-Username")).thenReturn(MOCKED_USERNAME);

        assertNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }

    @Test
    public void authenticateUserFailsWhenNoPrefUsername() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn(MOCKED_TOKEN);
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Preferred-Username")).thenReturn("");

        assertNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }

    @Test
    @SetEnvironmentVariable(key = OAUTH_2_PROXY_JWKS_ENDPOINT, value = JWKS_MOCK_ENDPOINT_URL)
    public void getUserContextSucceed() throws GuacamoleException {
        try (MockedStatic<ConnectionService> connectionServiceMockedStatic =
                 Mockito.mockStatic(ConnectionService.class)) {
            connectionServiceMockedStatic.when(() -> ConnectionService.getConnections(authenticatedUser))
                .thenReturn(new HashMap<String, Connection>());
            when(authenticatedUser.getAccessToken()).thenReturn(MOCKED_TOKEN);

            TreUserContext treUserContext =
                (TreUserContext) azureTREAuthenticationProvider.getUserContext(authenticatedUser);
            verify(authenticationProviderService).validateToken(anyString(), any(UrlJwkProvider.class));
            assertNotNull(treUserContext);
        }
    }

    @Test
    public void getUserContextFailsWhenNotInstanceOfAuthUser() throws GuacamoleException {
        AuthenticatedUser notTreUser = mock(AuthenticatedUser.class);
        assertNull(azureTREAuthenticationProvider.getUserContext(notTreUser));
    }

    @Test
    @SetEnvironmentVariable(key = OAUTH_2_PROXY_JWKS_ENDPOINT, value = JWKS_MOCK_ENDPOINT_URL)
    public void getUserContextFailsWhenTokenValidation() throws GuacamoleException {
        try (MockedStatic<ConnectionService> connectionServiceMockedStatic =
                 Mockito.mockStatic(ConnectionService.class)) {
            connectionServiceMockedStatic.when(() -> ConnectionService.getConnections(authenticatedUser))
                .thenReturn(new HashMap<String, Connection>());
            when(authenticatedUser.getAccessToken()).thenReturn(MOCKED_TOKEN);
            doThrow(new GuacamoleInvalidCredentialsException(
                "Could not validate token",
                CredentialsInfo.USERNAME_PASSWORD))
                .when(authenticationProviderService).validateToken(anyString(), any(UrlJwkProvider.class));
            assertNull(azureTREAuthenticationProvider.getUserContext(authenticatedUser));
        }
    }
}
