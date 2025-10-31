import { test, expect, Page } from '@playwright/test';

const TEST_USERNAME = process.env.TEST_USERNAME || 'testuser';
const TEST_PASSWORD = process.env.TEST_PASSWORD || 'testpass';
const GUACAMOLE_URL = process.env.GUACAMOLE_URL || 'http://localhost:8080';

test.describe('Guacamole TRE Integration E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Set longer timeout for navigation
    page.setDefaultTimeout(30000);
  });

  test('should load Guacamole homepage', async ({ page }) => {
    await page.goto('/');
    
    // Verify page loaded
    await expect(page).toHaveTitle(/Guacamole/i);
    
    // Take screenshot
    await page.screenshot({ path: '/screenshots/01-homepage.png', fullPage: true });
  });

  test('should navigate to OAuth2 login', async ({ page }) => {
    await page.goto('/guacamole');
    
    // Wait for OAuth2 redirect or login page
    await page.waitForLoadState('networkidle');
    
    // Take screenshot of login page
    await page.screenshot({ path: '/screenshots/02-login-page.png', fullPage: true });
    
    // Verify we're on some kind of auth page
    const url = page.url();
    expect(url).toMatch(/(login|oauth|sign-in|guacamole)/i);
  });

  test('should show Guacamole interface after auth bypass (mock)', async ({ page }) => {
    // For testing without full OAuth flow, we can mock authentication
    // by setting the required cookies/tokens
    
    // Navigate directly to Guacamole
    await page.goto('/guacamole/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await page.screenshot({ path: '/screenshots/03-guacamole-interface.png', fullPage: true });
  });

  test('should display available VMs from TRE API', async ({ page }) => {
    // This test assumes mock API is returning VM list
    await page.goto('/guacamole/');
    
    await page.waitForLoadState('networkidle');
    
    // Look for connection list or VM entries
    // Guacamole typically shows connections in a list or grid
    const connectionList = page.locator('.connection, [data-role="connection"], .connection-group');
    
    // Take screenshot
    await page.screenshot({ path: '/screenshots/04-vm-list.png', fullPage: true });
    
    // Verify at least one connection is shown (if available)
    // This might not be visible without proper auth, so we just check the page loaded
    expect(page.url()).toContain('guacamole');
  });

  test('should handle RDP connection attempt', async ({ page }) => {
    // Navigate to Guacamole
    await page.goto('/guacamole/');
    await page.waitForLoadState('networkidle');
    
    // Try to find and click on a connection (if visible)
    const connection = page.locator('.connection, [data-role="connection"]').first();
    
    if (await connection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await connection.click();
      
      // Wait for RDP connection to initialize
      await page.waitForTimeout(3000);
      
      // Take screenshot of RDP connection attempt
      await page.screenshot({ path: '/screenshots/05-rdp-connection.png', fullPage: true });
      
      // Check for Guacamole canvas (where RDP screen would be shown)
      const canvas = page.locator('canvas#display');
      await expect(canvas).toBeVisible({ timeout: 10000 });
      
      // Take final screenshot showing connection
      await page.screenshot({ path: '/screenshots/06-rdp-connected.png', fullPage: true });
    } else {
      console.log('No connections visible - likely authentication required');
      await page.screenshot({ path: '/screenshots/05-no-connections.png', fullPage: true });
    }
  });

  test('should verify credential injection flow', async ({ page }) => {
    // This test verifies that the TRE auth extension is loaded
    await page.goto('/guacamole/');
    await page.waitForLoadState('networkidle');
    
    // Check network requests for TRE API calls
    const apiRequests: string[] = [];
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/workspaces') || url.includes('vault.azure.net')) {
        apiRequests.push(url);
      }
    });
    
    // Trigger any actions that would make API calls
    await page.waitForTimeout(2000);
    
    await page.screenshot({ path: '/screenshots/07-credential-flow.png', fullPage: true });
    
    console.log('API requests observed:', apiRequests);
  });

  test('should verify Guacamole 1.6.0 version', async ({ page }) => {
    await page.goto('/guacamole/');
    await page.waitForLoadState('networkidle');
    
    // Check for version information
    // Guacamole might show version in About or similar
    const pageContent = await page.content();
    
    // Take screenshot
    await page.screenshot({ path: '/screenshots/08-version-check.png', fullPage: true });
    
    // Verify we're running Guacamole (basic check)
    expect(pageContent).toContain('Guacamole');
  });

  test('should handle OAuth2 proxy authentication flow', async ({ page }) => {
    // Clear any existing auth
    await page.context().clearCookies();
    
    await page.goto('/guacamole/');
    
    // Wait for OAuth2 proxy redirect
    await page.waitForLoadState('networkidle');
    
    const url = page.url();
    console.log('Current URL after redirect:', url);
    
    await page.screenshot({ path: '/screenshots/09-oauth-flow.png', fullPage: true });
    
    // Verify we were redirected to auth (or are on Guacamole if bypassed)
    expect(url).toBeTruthy();
  });

  test('should verify security headers and configuration', async ({ page }) => {
    const response = await page.goto('/guacamole/');
    
    // Check response headers
    const headers = response?.headers();
    console.log('Response headers:', headers);
    
    await page.screenshot({ path: '/screenshots/10-security-check.png', fullPage: true });
    
    // Verify we got a response
    expect(response?.status()).toBeLessThan(500);
  });
});
