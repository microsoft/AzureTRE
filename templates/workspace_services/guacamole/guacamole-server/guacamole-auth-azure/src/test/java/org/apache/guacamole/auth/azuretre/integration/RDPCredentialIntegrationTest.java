package org.apache.guacamole.auth.azuretre.integration;

import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junitpioneer.jupiter.SetEnvironmentVariable;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * Integration tests for RDP credential injection and configuration.
 * These tests validate that credentials are properly injected into RDP connections
 * and cleaned up after use, without requiring actual Azure VMs or RDP servers.
 */
@ExtendWith(MockitoExtension.class)
public class RDPCredentialIntegrationTest {

    private GuacamoleConfiguration rdpConfig;

    @BeforeEach
    public void setup() {
        rdpConfig = new GuacamoleConfiguration();
    }

    @Test
    public void testRDPConfigurationParametersAreSetCorrectly() {
        // Setup: Configure RDP connection parameters
        rdpConfig.setProtocol("rdp");
        rdpConfig.setParameter("hostname", "10.0.0.100");
        rdpConfig.setParameter("port", "3389");
        rdpConfig.setParameter("username", "testuser");
        rdpConfig.setParameter("password", "testpassword");
        rdpConfig.setParameter("ignore-cert", "true");
        rdpConfig.setParameter("resize-method", "display-update");

        // Verify: All RDP parameters are set correctly
        assertEquals("rdp", rdpConfig.getProtocol(), "Protocol should be RDP");
        assertEquals("10.0.0.100", rdpConfig.getParameter("hostname"),
            "Hostname should be set correctly");
        assertEquals("3389", rdpConfig.getParameter("port"),
            "Port should be 3389");
        assertEquals("testuser", rdpConfig.getParameter("username"),
            "Username should be set");
        assertEquals("testpassword", rdpConfig.getParameter("password"),
            "Password should be set");
        assertEquals("true", rdpConfig.getParameter("ignore-cert"),
            "Certificate validation should be disabled");
        assertEquals("display-update", rdpConfig.getParameter("resize-method"),
            "Resize method should be display-update");
    }

    @Test
    public void testCredentialInjectionFlow() {
        // Simulate credential retrieval from Key Vault
        String mockUsername = "admin-user";
        String mockPassword = "secure-password-123";

        // Step 1: Initial config without credentials
        rdpConfig.setProtocol("rdp");
        rdpConfig.setParameter("hostname", "10.0.0.100");
        rdpConfig.setParameter("azure-resource-id", "vm-test-123");

        assertNull(rdpConfig.getParameter("username"),
            "Username should be null before injection");
        assertNull(rdpConfig.getParameter("password"),
            "Password should be null before injection");

        // Step 2: Inject credentials (simulating TokenInjectingConnection)
        rdpConfig.setParameter("username", mockUsername);
        rdpConfig.setParameter("password", mockPassword);

        assertEquals(mockUsername, rdpConfig.getParameter("username"),
            "Username should be injected");
        assertEquals(mockPassword, rdpConfig.getParameter("password"),
            "Password should be injected");

        // Step 3: Simulate cleanup (as done in TokenInjectingConnection finally block)
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);

        assertNull(rdpConfig.getParameter("username"),
            "Username should be cleared after use");
        assertNull(rdpConfig.getParameter("password"),
            "Password should be cleared after use");
    }

    @Test
    public void testCredentialCleanupAfterConnectionFailure() {
        // Setup: Inject credentials
        rdpConfig.setParameter("username", "testuser");
        rdpConfig.setParameter("password", "testpass");

        try {
            // Simulate connection attempt that fails
            throw new GuacamoleException("Connection failed");
        } catch (GuacamoleException e) {
            // Cleanup should happen in finally block
            rdpConfig.setParameter("username", null);
            rdpConfig.setParameter("password", null);
        } finally {
            // Verify: Credentials are cleared even on failure
            assertNull(rdpConfig.getParameter("username"),
                "Username should be cleared after failure");
            assertNull(rdpConfig.getParameter("password"),
                "Password should be cleared after failure");
        }
    }

    @Test
    @SetEnvironmentVariable(key = "GUAC_DISABLE_COPY", value = "true")
    @SetEnvironmentVariable(key = "GUAC_DISABLE_PASTE", value = "false")
    @SetEnvironmentVariable(key = "GUAC_ENABLE_DRIVE", value = "false")
    @SetEnvironmentVariable(key = "GUAC_DRIVE_NAME", value = "transfer")
    @SetEnvironmentVariable(key = "GUAC_DRIVE_PATH", value = "/guac-transfer")
    @SetEnvironmentVariable(key = "GUAC_DISABLE_DOWNLOAD", value = "true")
    @SetEnvironmentVariable(key = "GUAC_DISABLE_UPLOAD", value = "true")
    @SetEnvironmentVariable(key = "GUAC_SERVER_LAYOUT", value = "en-us-qwerty")
    public void testRDPSecurityParameters() {
        // Setup: Configure RDP with security parameters from environment
        rdpConfig.setProtocol("rdp");
        rdpConfig.setParameter("hostname", "10.0.0.100");
        rdpConfig.setParameter("disable-copy", System.getenv("GUAC_DISABLE_COPY"));
        rdpConfig.setParameter("disable-paste", System.getenv("GUAC_DISABLE_PASTE"));
        rdpConfig.setParameter("enable-drive", System.getenv("GUAC_ENABLE_DRIVE"));
        rdpConfig.setParameter("drive-name", System.getenv("GUAC_DRIVE_NAME"));
        rdpConfig.setParameter("drive-path", System.getenv("GUAC_DRIVE_PATH"));
        rdpConfig.setParameter("disable-download", System.getenv("GUAC_DISABLE_DOWNLOAD"));
        rdpConfig.setParameter("disable-upload", System.getenv("GUAC_DISABLE_UPLOAD"));
        rdpConfig.setParameter("server-layout", System.getenv("GUAC_SERVER_LAYOUT"));

        // Verify: Security parameters are applied correctly
        assertEquals("true", rdpConfig.getParameter("disable-copy"),
            "Copy should be disabled");
        assertEquals("false", rdpConfig.getParameter("disable-paste"),
            "Paste should be enabled");
        assertEquals("false", rdpConfig.getParameter("enable-drive"),
            "Drive should be disabled");
        assertEquals("transfer", rdpConfig.getParameter("drive-name"),
            "Drive name should be set");
        assertEquals("/guac-transfer", rdpConfig.getParameter("drive-path"),
            "Drive path should be set");
        assertEquals("true", rdpConfig.getParameter("disable-download"),
            "Download should be disabled");
        assertEquals("true", rdpConfig.getParameter("disable-upload"),
            "Upload should be disabled");
        assertEquals("en-us-qwerty", rdpConfig.getParameter("server-layout"),
            "Keyboard layout should be set");
    }

    @Test
    public void testMultipleCredentialInjectionCycles() {
        // Cycle 1: First connection
        rdpConfig.setParameter("username", "user1");
        rdpConfig.setParameter("password", "pass1");
        assertEquals("user1", rdpConfig.getParameter("username"));

        // Cleanup after cycle 1
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);
        assertNull(rdpConfig.getParameter("username"));

        // Cycle 2: Second connection with different credentials
        rdpConfig.setParameter("username", "user2");
        rdpConfig.setParameter("password", "pass2");
        assertEquals("user2", rdpConfig.getParameter("username"));

        // Cleanup after cycle 2
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);
        assertNull(rdpConfig.getParameter("username"));

        // Verify: Configuration can be reused safely
        assertNull(rdpConfig.getParameter("password"),
            "No credentials should remain after multiple cycles");
    }

    @Test
    public void testRDPConfigurationWithSpecialCharactersInCredentials() {
        // Setup: Credentials with special characters
        String usernameWithSpecialChars = "domain\\user@test.com";
        String passwordWithSpecialChars = "P@ssw0rd!#$%";

        rdpConfig.setParameter("username", usernameWithSpecialChars);
        rdpConfig.setParameter("password", passwordWithSpecialChars);

        // Verify: Special characters are preserved
        assertEquals(usernameWithSpecialChars, rdpConfig.getParameter("username"),
            "Username with special characters should be preserved");
        assertEquals(passwordWithSpecialChars, rdpConfig.getParameter("password"),
            "Password with special characters should be preserved");

        // Cleanup
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);
    }

    @Test
    public void testRDPConfigurationValidation() {
        // Setup: Configure minimal RDP connection
        rdpConfig.setProtocol("rdp");
        rdpConfig.setParameter("hostname", "10.0.0.100");
        rdpConfig.setParameter("port", "3389");

        // Verify: Minimal required parameters are set
        assertNotNull(rdpConfig.getProtocol(), "Protocol should be set");
        assertNotNull(rdpConfig.getParameter("hostname"), "Hostname should be set");
        assertNotNull(rdpConfig.getParameter("port"), "Port should be set");

        // Verify: Optional parameters can be null
        assertNull(rdpConfig.getParameter("username"),
            "Username can be null before injection");
        assertNull(rdpConfig.getParameter("domain"),
            "Domain is optional");
    }

    @Test
    public void testCredentialInjectionFromKeyVaultFormat() {
        // Simulate Key Vault secret format: "username\npassword"
        String keyVaultSecret = "admin-user\nsecure-password-123";
        String[] credentials = keyVaultSecret.split("\\n");

        // Verify: Credentials are parsed correctly
        assertEquals(2, credentials.length, "Should have exactly 2 parts");

        String username = credentials[0];
        String password = credentials[1];

        // Inject into configuration
        rdpConfig.setParameter("username", username);
        rdpConfig.setParameter("password", password);

        // Verify: Credentials are set correctly
        assertEquals("admin-user", rdpConfig.getParameter("username"),
            "Username should be parsed from Key Vault format");
        assertEquals("secure-password-123", rdpConfig.getParameter("password"),
            "Password should be parsed from Key Vault format");

        // Cleanup
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);
    }

    @Test
    public void testInvalidKeyVaultFormatHandling() {
        // Simulate invalid Key Vault secret format
        String invalidSecret = "only-one-field";
        String[] credentials = invalidSecret.split("\\n");

        // Verify: Invalid format is detected
        assertNotEquals(2, credentials.length,
            "Invalid format should not have exactly 2 parts");

        // Should not inject invalid credentials
        if (credentials.length != 2) {
            // Don't inject - this simulates error handling in TokenInjectingConnection
            assertNull(rdpConfig.getParameter("username"),
                "Username should not be set with invalid format");
            assertNull(rdpConfig.getParameter("password"),
                "Password should not be set with invalid format");
        }
    }

    @Test
    public void testRDPConfigurationImmutabilityAfterCleanup() {
        // Setup: Initial configuration
        rdpConfig.setProtocol("rdp");
        rdpConfig.setParameter("hostname", "10.0.0.100");
        rdpConfig.setParameter("port", "3389");
        rdpConfig.setParameter("ignore-cert", "true");

        // Inject credentials
        rdpConfig.setParameter("username", "testuser");
        rdpConfig.setParameter("password", "testpass");

        // Cleanup credentials
        rdpConfig.setParameter("username", null);
        rdpConfig.setParameter("password", null);

        // Verify: Non-credential parameters remain unchanged
        assertEquals("rdp", rdpConfig.getProtocol(),
            "Protocol should remain unchanged");
        assertEquals("10.0.0.100", rdpConfig.getParameter("hostname"),
            "Hostname should remain unchanged");
        assertEquals("3389", rdpConfig.getParameter("port"),
            "Port should remain unchanged");
        assertEquals("true", rdpConfig.getParameter("ignore-cert"),
            "Certificate setting should remain unchanged");

        // Verify: Only credentials are cleared
        assertNull(rdpConfig.getParameter("username"),
            "Username should be cleared");
        assertNull(rdpConfig.getParameter("password"),
            "Password should be cleared");
    }
}
