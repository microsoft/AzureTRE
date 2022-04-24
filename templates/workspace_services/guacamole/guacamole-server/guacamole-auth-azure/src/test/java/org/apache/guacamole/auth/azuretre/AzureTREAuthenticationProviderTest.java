package org.apache.guacamole.auth.azuretre;

import org.apache.guacamole.net.auth.Credentials;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import javax.servlet.http.HttpServletRequest;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)

public class AzureTREAuthenticationProviderTest {
    @Mock
    HttpServletRequest requestMock;
    @InjectMocks
    Credentials credentialsMock;
    AzureTREAuthenticationProvider azureTREAuthenticationProvider;

    @BeforeEach
    void setup() {
        azureTREAuthenticationProvider = new AzureTREAuthenticationProvider();
    }

    @Test
    public void authenticateUserSucceed() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn("dummy_token");
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Email")).thenReturn("mocked@mail.com");

        assertNotNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }

    @Test
    public void authenticateUserFailsWhenNoAccessToken() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn("");
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Email")).thenReturn("mocked@mail.com");

        assertNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }

    @Test
    public void authenticateUserFailsWhenNoPrefEmail() {
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Access-Token")).thenReturn("dummy_token");
        when(credentialsMock.getRequest().getHeader("X-Forwarded-Email")).thenReturn("");

        assertNull(azureTREAuthenticationProvider.authenticateUser(credentialsMock));
    }
}
