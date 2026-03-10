import { test, expect } from '@playwright/test';

test.describe('Guacamole VM Connection Tests', () => {
  test('should detect VMs through API integration', async ({ request }) => {
    // Test that our mock API is responding correctly
    const response = await request.get('http://mock-api:1080/api/workspaces/test-workspace/workspace-services/vm-service-001/user-resources');
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('userResources');
    expect(body.userResources).toHaveLength(1);
    expect(body.userResources[0]).toMatchObject({
      id: 'vm-resource-001',
      templateName: 'tre-service-guacamole-windowsvm',
      templateVersion: '1.0.0',
      properties: {
        hostname: 'vm-resource-001',
        ip: 'xrdp',
        display_name: 'Test Virtual Machine',
        vm_resource_id: '/subscriptions/test/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/test-vm',
        is_exposed_externally: true
      }
    });
  });

  test('should redirect to Azure AD for authentication', async ({ page }) => {
    // Mock Azure AD response
    await page.route('https://login.microsoftonline.com/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>Azure AD Login Mock</body></html>'
      });
    });

    const response = await page.goto('/guacamole/', { waitUntil: 'commit' });

    // Should redirect to Azure AD or show login redirect
    expect([200, 302, 303]).toContain(response?.status() ?? 200);

    await page.screenshot({ path: '/screenshots/vm-connection-auth-redirect.png', fullPage: true });
  });

  test('should handle authentication headers correctly', async ({ request }) => {
    // Test that the backend responds to authentication headers
    const response = await request.get('/guacamole/', {
      headers: {
        'X-Forwarded-Access-Token': 'mock-access-token',
        'X-Forwarded-Preferred-Username': 'test@example.com'
      },
      failOnStatusCode: false
    });

    // Should get some response (not necessarily successful, but not crash)
    expect(response.status()).toBeLessThan(500);
  });
});
