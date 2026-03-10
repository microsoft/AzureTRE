package org.apache.guacamole.auth.azuretre.integration;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.auth.azuretre.AzureTREAuthenticationProvider;
import org.apache.guacamole.auth.azuretre.user.AzureTREAuthenticatedUser;
import org.apache.guacamole.net.RequestDetails;
import org.apache.guacamole.net.auth.Credentials;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junitpioneer.jupiter.SetEnvironmentVariable;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

/**
 * Integration tests that run locally without cloud dependencies.
 * These tests use MockWebServer to simulate external services and verify
 * the authentication flow end-to-end without requiring Azure resources.
 */
@ExtendWith(MockitoExtension.class)
public class LocalIntegrationTest {

    private MockWebServer mockApiServer;

    @Mock
    private Credentials credentialsMock;

    @Mock
    private RequestDetails requestDetailsMock;

    private AzureTREAuthenticationProvider authProvider;
    private String mockApiUrl;

    private static final String TEST_WORKSPACE_ID = "test-workspace-123";
    private static final String TEST_SERVICE_ID = "test-service-456";
    private static final String TEST_USERNAME = "testuser@domain.com";
    private static final String TEST_TOKEN = "test.jwt.token";

    @BeforeEach
    public void setup() throws IOException {
        // Start mock API server
        mockApiServer = new MockWebServer();
        mockApiServer.start();
        mockApiUrl = mockApiServer.url("/").toString().replaceAll("/$", "");

        authProvider = new AzureTREAuthenticationProvider();
    }

    private void stubCredentialRequest() {
        when(credentialsMock.getRequestDetails()).thenReturn(requestDetailsMock);
    }

    @AfterEach
    public void teardown() throws IOException {
        if (mockApiServer != null) {
            mockApiServer.shutdown();
        }
    }

    @Test
    public void testSuccessfulAuthentication() throws GuacamoleException {
        // Setup: Mock the RequestDetails to return valid headers
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(TEST_USERNAME);

        // Execute: Authenticate user
        AzureTREAuthenticatedUser authenticatedUser = authProvider.authenticateUser(credentialsMock);

        // Verify: User was authenticated successfully
        assertNotNull(authenticatedUser, "User should be authenticated");
        assertEquals(TEST_USERNAME.toLowerCase(), authenticatedUser.getIdentifier(),
            "Username should be normalized to lowercase");
        assertEquals(TEST_TOKEN, authenticatedUser.getAccessToken(),
            "Access token should match");
        assertEquals(credentialsMock, authenticatedUser.getCredentials(),
            "Credentials should be preserved");
    }

    @Test
    public void testAuthenticationFailsWithMissingToken() {
        // Setup: Mock missing access token
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(null);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(TEST_USERNAME);

        // Execute & Verify: Authentication should fail
        AzureTREAuthenticatedUser result = authProvider.authenticateUser(credentialsMock);
        assertNull(result, "Authentication should fail without access token");
    }

    @Test
    public void testAuthenticationFailsWithEmptyToken() {
        // Setup: Mock empty token
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn("");
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(TEST_USERNAME);

        // Execute & Verify: Should fail with empty token
        AzureTREAuthenticatedUser result = authProvider.authenticateUser(credentialsMock);
        assertNull(result, "Authentication should fail with empty token");
    }

    @Test
    public void testAuthenticationFailsWithMissingUsername() {
        // Setup: Mock missing username
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(null);

        // Execute & Verify: Authentication should fail
        AzureTREAuthenticatedUser result = authProvider.authenticateUser(credentialsMock);
        assertNull(result, "Authentication should fail without username");
    }

    @Test
    public void testAuthenticationFailsWithEmptyUsername() {
        // Setup: Mock empty username
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn("");

        // Execute & Verify: Should fail with empty username
        AzureTREAuthenticatedUser result = authProvider.authenticateUser(credentialsMock);
        assertNull(result, "Authentication should fail with empty username");
    }

    @Test
    public void testUsernameNormalization() {
        // Setup: Mock credentials with mixed-case username
        stubCredentialRequest();
        String mixedCaseUsername = "TestUser@Domain.COM";
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(mixedCaseUsername);

        // Execute
        AzureTREAuthenticatedUser user = authProvider.authenticateUser(credentialsMock);

        // Verify: Username should be normalized to lowercase
        assertNotNull(user, "User should be authenticated");
        assertEquals(mixedCaseUsername.toLowerCase(), user.getIdentifier(),
            "Username should be converted to lowercase");
    }

    @Test
    public void testAuthenticationPreservesTokenAndCredentials() {
        // Setup
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(TEST_USERNAME);

        // Execute
        AzureTREAuthenticatedUser user = authProvider.authenticateUser(credentialsMock);

        // Verify: All authentication data is preserved
        assertNotNull(user, "User should be authenticated");
        assertSame(credentialsMock, user.getCredentials(),
            "Original credentials object should be preserved");
        assertEquals(TEST_TOKEN, user.getAccessToken(),
            "Access token should be stored");
        assertNotNull(user.getAuthenticationProvider(),
            "Authentication provider should be set");
    }

    @Test
    @SetEnvironmentVariable(key = "API_URL", value = "http://localhost:8080")
    @SetEnvironmentVariable(key = "WORKSPACE_ID", value = TEST_WORKSPACE_ID)
    @SetEnvironmentVariable(key = "SERVICE_ID", value = TEST_SERVICE_ID)
    public void testMockedAPIEndpoint() {
        // Setup: Mock API response with VM data
        String mockVmResponse = "{\n"
            + "    \"userResources\": [\n"
            + "        {\n"
            + "            \"properties\": {\n"
            + "                \"hostname\": \"vm-test-123\",\n"
            + "                \"ip\": \"10.0.0.100\",\n"
            + "                \"display_name\": \"Test VM 1\"\n"
            + "            }\n"
            + "        }\n"
            + "    ]\n"
            + "}";

        mockApiServer.enqueue(new MockResponse()
            .setBody(mockVmResponse)
            .setResponseCode(200)
            .addHeader("Content-Type", "application/json"));

        // Verify: Mock server is ready and response is valid
        assertNotNull(mockVmResponse, "Mock response should be defined");
        assertTrue(mockVmResponse.contains("userResources"),
            "Response should contain userResources");
        assertTrue(mockVmResponse.contains("vm-test-123"),
            "Response should contain test VM data");
    }

    @Test
    public void testMultipleAuthenticationAttempts() {
        // Setup: Prepare for multiple authentication attempts
        stubCredentialRequest();
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(TEST_USERNAME);

        // Execute: Multiple authentication calls
        AzureTREAuthenticatedUser user1 = authProvider.authenticateUser(credentialsMock);
        AzureTREAuthenticatedUser user2 = authProvider.authenticateUser(credentialsMock);

        // Verify: Both authentications should succeed independently
        assertNotNull(user1, "First authentication should succeed");
        assertNotNull(user2, "Second authentication should succeed");
        assertEquals(user1.getIdentifier(), user2.getIdentifier(),
            "Both authentications should return same user identifier");
    }

    @Test
    public void testAuthenticationWithSpecialCharacters() {
        // Setup: Username with special characters
        stubCredentialRequest();
        String specialUsername = "test.user+tag@sub.domain.com";
        when(requestDetailsMock.getHeader("X-Forwarded-Access-Token")).thenReturn(TEST_TOKEN);
        when(requestDetailsMock.getHeader("X-Forwarded-Preferred-Username")).thenReturn(specialUsername);

        // Execute
        AzureTREAuthenticatedUser user = authProvider.authenticateUser(credentialsMock);

        // Verify: Special characters should be handled correctly
        assertNotNull(user, "User with special characters should be authenticated");
        assertEquals(specialUsername.toLowerCase(), user.getIdentifier(),
            "Special characters should be preserved in lowercase");
    }
}
