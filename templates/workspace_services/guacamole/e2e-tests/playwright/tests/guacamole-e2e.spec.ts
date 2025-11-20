import { test, expect } from '@playwright/test';

const OAUTH_LOGIN_URL_REGEX = /(login\.microsoftonline\.com|oauth2\/(start|auth|callback))/i;

test.describe('Guacamole TRE OAuth-protected E2E checks', () => {
  test('redirects unauthenticated users to Azure AD', async ({ request }) => {
    const response = await request.get('/guacamole/', {
      failOnStatusCode: false,
      maxRedirects: 0,
    });

    expect([200, 302, 303]).toContain(response.status());

    const locationHeader = response.headers()['location'] ?? '';
    if (locationHeader) {
      expect(locationHeader).toMatch(OAUTH_LOGIN_URL_REGEX);
    } else {
      expect(response.url()).toMatch(OAUTH_LOGIN_URL_REGEX);
    }
  });

  test('browser navigation tries to reach Azure AD login', async ({ page }) => {
    await page.route('https://login.microsoftonline.com/**', route => {
      route.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>Azure AD Stub</body></html>' });
    });

    const response = await page.goto('/guacamole/', { waitUntil: 'commit' });
    const redirectLocation = response?.headers()['location'];

    if (redirectLocation) {
      expect(response?.status()).toBe(302);
      expect(redirectLocation).toMatch(OAUTH_LOGIN_URL_REGEX);
    } else {
      // When Playwright follows the redirect, assert the current URL instead.
      expect(page.url()).toMatch(OAUTH_LOGIN_URL_REGEX);
    }

    await page.screenshot({ path: '/screenshots/01-login-redirect.png', fullPage: true });
  });

  test('blocks REST API access without authentication', async ({ request }) => {
    const response = await request.get('/guacamole/api/session/data', {
      failOnStatusCode: false,
      maxRedirects: 0,
    });

    expect([200, 302, 303, 401, 403]).toContain(response.status());

    if (response.status() === 200) {
      const body = await response.text();
      expect(body).toMatch(/<html/i);
      expect(response.url()).toMatch(OAUTH_LOGIN_URL_REGEX);
    }
  });

  test('exposes oauth2-proxy ping endpoint', async ({ request }) => {
    const response = await request.get('http://guacamole-backend:8085/ping');
    expect(response.status()).toBe(200);
    expect(await response.text()).toContain('OK');
  });

  test('enforces security headers on protected resources', async ({ request }) => {
    const response = await request.get('/guacamole/', {
      failOnStatusCode: false,
      maxRedirects: 0,
    });

    const headers = response.headers();

    expect(headers['cache-control']).toBeDefined();
    expect(response.status()).toBeLessThan(500);
  });
});
