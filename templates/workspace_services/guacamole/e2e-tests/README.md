# Guacamole TRE End-to-End Tests

This directory contains end-to-end tests for the Guacamole TRE integration using Docker Compose and Playwright.

## Overview

The E2E test suite validates the complete Guacamole workflow including:
- OAuth2 proxy authentication
- TRE API integration
- VM connection listing
- RDP credential injection
- End-to-end connection flow

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Playwright │────▶│   Guacamole    │────▶│   Mock API   │
│   (Tests)    │     │  + TRE Auth    │     │   (TRE API)  │
└──────────────┘     └─────────────────┘     └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │     xrdp     │
                      │  (Test RDP)  │
                      └──────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Network access to:
  - Maven Central (for building Guacamole auth extension)
  - Apache mirrors (for Guacamole and Tomcat downloads)
  - Docker Hub (for base images)
  - GitHub (for oauth2-proxy and other dependencies)

## Setup

1. **Build the Guacamole Image** (if not already built):
   ```bash
   cd ../guacamole-server
   docker build -f docker/Dockerfile -t guacamole-tre:latest .
   ```

2. **Start the Test Environment**:
   ```bash
   docker-compose up -d
   ```

3. **Run the Tests**:
   ```bash
   # Run tests in the Playwright container
   docker-compose run playwright npx playwright test

   # Or run tests locally (if Playwright is installed)
   cd playwright
   npm install
   GUACAMOLE_URL=http://localhost:8080 npx playwright test
   ```

## Test Cases

### 1. Homepage Load Test
- **Purpose**: Verify Guacamole homepage loads correctly
- **Screenshot**: `01-homepage.png`

### 2. OAuth2 Login Navigation
- **Purpose**: Verify OAuth2 proxy redirects to authentication
- **Screenshot**: `02-login-page.png`

### 3. Guacamole Interface Display
- **Purpose**: Verify Guacamole UI loads after authentication
- **Screenshot**: `03-guacamole-interface.png`

### 4. VM List Display
- **Purpose**: Verify VMs from TRE API are displayed
- **Screenshot**: `04-vm-list.png`

### 5. RDP Connection Attempt
- **Purpose**: Verify RDP connection can be initiated
- **Screenshots**: `05-rdp-connection.png`, `06-rdp-connected.png`

### 6. Credential Injection Flow
- **Purpose**: Verify TRE auth extension makes correct API calls
- **Screenshot**: `07-credential-flow.png`

### 7. Version Verification
- **Purpose**: Confirm Guacamole 1.6.0 is running
- **Screenshot**: `08-version-check.png`

### 8. OAuth2 Authentication Flow
- **Purpose**: Verify OAuth2 proxy handles authentication correctly
- **Screenshot**: `09-oauth-flow.png`

### 9. Security Headers Check
- **Purpose**: Verify security headers are properly configured
- **Screenshot**: `10-security-check.png`

## Screenshots

All test screenshots are saved to `./playwright/screenshots/` and can be used to verify:
- Visual regression
- UI functionality
- Connection states
- Error conditions

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUACAMOLE_URL` | `http://localhost:8080` | Guacamole server URL |
| `XRDP_HOST` | `xrdp` | xrdp server hostname |
| `XRDP_PORT` | `3389` | xrdp server port |
| `TEST_USERNAME` | `testuser` | Test username for RDP |
| `TEST_PASSWORD` | `testpass` | Test password for RDP |

### Mock API Configuration

The mock API (`mock-api-config.json`) simulates TRE API responses for:
- Workspace services list
- User resources (VMs) list

Modify this file to test different scenarios.

## Troubleshooting

### Docker Build Fails

If the Guacamole Docker build fails with SSL/certificate errors:
1. Ensure firewall rules allow access to required domains
2. Check that Docker can access Maven Central and Apache mirrors
3. Review the Dockerfile for Java 17 and ca-certificates configuration

### Tests Fail to Connect

If Playwright tests cannot reach Guacamole:
1. Verify all containers are running: `docker-compose ps`
2. Check container logs: `docker-compose logs guacamole`
3. Ensure ports are not already in use
4. Verify network connectivity: `docker-compose exec playwright ping guacamole`

### No VMs Displayed

If no VMs appear in Guacamole:
1. Check mock API is responding: `curl http://localhost:8000/api/workspaces/test-workspace/workspace-services/`
2. Verify TRE auth extension is loaded in Guacamole logs
3. Check authentication is properly bypassed for testing

## Cleanup

```bash
# Stop all containers
docker-compose down

# Remove volumes and networks
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

## CI/CD Integration

To run these tests in CI/CD:

```yaml
# Example GitHub Actions workflow
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests
        run: |
          cd templates/workspace_services/guacamole/e2e-tests
          docker-compose up -d
          docker-compose run playwright npx playwright test
      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-screenshots
          path: templates/workspace_services/guacamole/e2e-tests/playwright/screenshots/
```

## Development

To add new tests:
1. Add test cases to `playwright/tests/guacamole-e2e.spec.ts`
2. Follow the existing pattern for screenshots and assertions
3. Update this README with new test documentation

## References

- [Playwright Documentation](https://playwright.dev/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Guacamole Documentation](https://guacamole.apache.org/doc/gug/)
- [Azure TRE Documentation](https://microsoft.github.io/AzureTRE/)
