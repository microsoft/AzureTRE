# Guacamole Development Container

This devcontainer provides a complete development environment for the Guacamole workspace service, including:

- **Java 17** - For building the Guacamole TRE authentication extension
- **Maven 3.9** - For Java dependency management and builds
- **Node.js 20** - For Playwright E2E tests
- **Playwright** - For browser automation and UI testing
- **Docker-in-Docker** - For running E2E test containers

## Getting Started

### Opening the Devcontainer

1. Open VS Code in the repository root
2. Press `F1` and select **Dev Containers: Open Folder in Container...**
3. Navigate to `templates/workspace_services/guacamole`
4. Select **Open** - VS Code will build and start the devcontainer

Alternatively, if you already have the repo open:
1. Press `F1`
2. Select **Dev Containers: Reopen in Container**
3. The devcontainer will use the guacamole-specific configuration

### First Time Setup

After the container starts, the `post-create.sh` script will automatically:
- Install Playwright system dependencies
- Build the Java authentication extension
- Install Node.js packages for E2E tests
- Install Playwright browsers
- Set up helpful command aliases

This may take a few minutes on first run.

## Available Commands

Once inside the devcontainer, run `guac-help` to see all available commands:

### Java Development
```bash
mvn-build    # Build the authentication extension
mvn-test     # Run unit and integration tests (66 tests)
```

### E2E Testing
```bash
e2e-build    # Build Docker Compose test environment
e2e-up       # Start test services (Guacamole, xrdp, mock API)
e2e-down     # Stop test services
e2e-test     # Run Playwright E2E tests (headless)
e2e-ui       # Run Playwright tests in UI mode
e2e-logs     # View logs from test services
```

## Quick Start Workflow

```bash
# 1. Build the Java extension
mvn-build

# 2. Build E2E test containers
e2e-build

# 3. Start the test environment
e2e-up

# 4. Run E2E tests
e2e-test

# 5. View results
ls e2e-tests/playwright/screenshots/
```

## Forwarded Ports

The devcontainer automatically forwards these ports:

- **8080** - Guacamole web interface
- **3000** - Mock TRE API (for E2E tests)
- **4200** - Playwright UI mode
- **5900** - VNC (for debugging)
- **3389** - RDP (for debugging)

## Extensions Installed

The devcontainer includes these VS Code extensions:

- Java Extension Pack - Full Java IDE support
- Maven for Java - Maven project management
- Playwright Test for VSCode - Run and debug Playwright tests
- ESLint - TypeScript/JavaScript linting
- Prettier - Code formatting
- Docker - Docker file support
- YAML - YAML file support

## Development Tips

### Running Java Tests
```bash
cd guacamole-server/guacamole-auth-azure
mvn test                                    # All tests
mvn test -Dtest=LocalIntegrationTest        # Integration tests only
mvn test -Dtest=RDPCredentialIntegrationTest # RDP tests only
```

### Running E2E Tests Individually
```bash
cd e2e-tests/playwright
npm test                                    # All tests
npm test -- --headed                        # With browser visible
npm test -- --project=chromium              # Specific browser
npm run test:ui                             # Interactive UI mode
```

### Debugging
- Set breakpoints in Java code - the Java debugger will attach automatically
- Use Playwright Inspector for E2E tests: `npx playwright test --debug`
- View Docker logs: `e2e-logs`

### Building Docker Image Locally
```bash
cd guacamole-server/docker
docker build -t tre-guacamole:local .
```

## Workspace Layout

The devcontainer sets the workspace root to the guacamole directory:

```
/workspaces/${repo-name}/templates/workspace_services/guacamole/
├── .devcontainer/           # This configuration
├── e2e-tests/              # E2E test infrastructure
│   ├── docker-compose.yml
│   ├── playwright/         # Playwright tests
│   └── run-tests.sh
├── guacamole-server/
│   ├── docker/            # Dockerfile
│   └── guacamole-auth-azure/  # Java extension
├── porter.yaml
└── template_schema.json
```

## Troubleshooting

### "Cannot connect to Docker daemon"
The devcontainer needs access to Docker. Ensure:
- Docker Desktop is running (on Mac/Windows)
- Your user has Docker permissions (on Linux)

### Playwright tests fail with "Browser not found"
Run: `cd e2e-tests/playwright && npx playwright install chromium`

### Maven build fails with certificate errors
The devcontainer uses Java 17 with updated CA certificates. If you still see errors:
```bash
sudo update-ca-certificates
```

### Ports already in use
Stop any local services using ports 8080, 3000, or 4200:
```bash
e2e-down  # Stop E2E environment
```

## CI/CD Integration

The E2E tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run E2E Tests
  run: |
    cd templates/workspace_services/guacamole/e2e-tests
    ./run-tests.sh full
```

## Additional Resources

- [Guacamole 1.6.0 Documentation](https://guacamole.apache.org/doc/1.6.0/gug/)
- [Playwright Documentation](https://playwright.dev/)
- [Azure TRE Documentation](https://microsoft.github.io/AzureTRE/)
