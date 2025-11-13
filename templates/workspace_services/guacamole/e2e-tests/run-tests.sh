#!/bin/bash
# Guacamole E2E Test Runner
# This script simplifies running the end-to-end tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="$SCRIPT_DIR/.env"

load_env_file() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        . "$ENV_FILE"
        set +a
    fi
}

require_auth_env() {
    local missing=()
    for var in GUAC_OIDC_TENANT_ID GUAC_OIDC_CLIENT_ID GUAC_OIDC_CLIENT_SECRET GUAC_OIDC_REDIRECT_URI GUAC_OIDC_ISSUER_URL GUAC_OIDC_AUDIENCE GUAC_OIDC_JWKS_URL; do
        if [ -z "${!var:-}" ]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}Missing Azure auth configuration:${NC} ${missing[*]}"
        echo "Run: $0 setup-auth"
        exit 1
    fi
}

load_env_file

COMPOSE_STARTED=0
APP_CREATED=0
APP_DELETED=0

delete_app_registration() {
    APP_DELETED=0
    if [ -z "${GUAC_OIDC_CLIENT_ID:-}" ]; then
        return
    fi

    if ! command -v az >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Azure CLI not available; skipping app registration deletion${NC}"
        return
    fi

    echo -e "${YELLOW}Cleaning up Azure AD app registration ${GUAC_OIDC_CLIENT_ID}${NC}"
    if az ad app delete --id "${GUAC_OIDC_CLIENT_ID}" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Deleted Azure AD app registration${NC}"
        APP_DELETED=1
    else
        echo -e "${YELLOW}⚠ Failed to delete Azure AD app registration (it may already be removed)${NC}"
    fi

    az ad sp delete --id "${GUAC_OIDC_CLIENT_ID}" >/dev/null 2>&1 || true
    return 0
}

cleanup_all() {
    set +e
    if [ "$COMPOSE_STARTED" -eq 1 ]; then
        docker compose down >/dev/null 2>&1
        COMPOSE_STARTED=0
    fi

    if [ "$APP_CREATED" -eq 1 ]; then
        delete_app_registration
        if [ "$APP_DELETED" -eq 1 ] && [ -f "$ENV_FILE" ]; then
            rm -f "$ENV_FILE"
        fi
        APP_CREATED=0
    fi
    set -e
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

validate_service() {
    local service="$1"

    if [ -z "$service" ]; then
        echo -e "${RED}✗ No service name provided${NC}"
        exit 1
    fi

    local valid_services
    if ! valid_services=$(docker compose config --services 2>/dev/null); then
        echo -e "${RED}✗ Unable to list services from docker compose. Is Docker running?${NC}"
        exit 1
    fi

    if ! printf '%s\n' "$valid_services" | grep -Fx -- "$service" >/dev/null; then
        echo -e "${RED}✗ Invalid service '${service}'. Available services:${NC}"
        printf '  - %s\n' $valid_services
        exit 1
    fi
}

echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Guacamole TRE E2E Test Suite${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo

# Function to print section headers
print_section() {
    echo
    echo -e "${YELLOW}▶ $1${NC}"
    echo
}

build_playwright_image() {
    print_section "Building Playwright test runner image..."
    docker compose build playwright
}

configure_mock_api() {
    if ! command -v curl >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ curl is not available; skipping mock API configuration${NC}"
        return 0
    fi

    local expectations_file="${SCRIPT_DIR}/config/expectations.json"
    if [ ! -f "$expectations_file" ]; then
        echo -e "${YELLOW}⚠ Mock expectations file not found at $expectations_file; skipping configuration${NC}"
        return 0
    fi

    print_section "Configuring mock TRE API expectations..."

    curl -s -X PUT "http://localhost:8000/mockserver/reset" >/dev/null 2>&1 || true

    local attempts=30
    while [ "$attempts" -gt 0 ]; do
        if curl -sf -X PUT "http://localhost:8000/mockserver/expectation" \
            -H "Content-Type: application/json" \
            --data-binary "@$expectations_file" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Mock TRE API expectations configured${NC}"
            return 0
        fi

        sleep 2
        attempts=$((attempts - 1))
    done

    echo -e "${RED}✗ Failed to configure mock TRE API expectations${NC}"
    return 1
}

# Parse command line arguments
COMMAND=${1:-help}

case "$COMMAND" in
    build)
        print_section "Building Guacamole Docker image..."
        cd ../guacamole-server
        docker build -f docker/Dockerfile -t guacamole-tre:latest .
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;

    setup-auth)
        print_section "Creating Azure AD app registration for tests..."
        scripts/setup-azure-auth.sh
        load_env_file
        APP_CREATED=1
        echo -e "${GREEN}✓ Azure AD configuration ready${NC}"
        ;;

    up)
        require_auth_env
        print_section "Starting test environment..."
        docker compose up -d
        COMPOSE_STARTED=1
        configure_mock_api
        echo
        echo -e "${GREEN}✓ Environment started${NC}"
        echo
        echo "Services running:"
        docker compose ps
        ;;

    down)
        require_auth_env
        print_section "Stopping test environment..."
        docker compose down
        COMPOSE_STARTED=0
        echo -e "${GREEN}✓ Environment stopped${NC}"
        ;;

    test)
        require_auth_env
        build_playwright_image
        configure_mock_api
        print_section "Running Playwright tests..."
        docker compose run --rm playwright npx playwright test
        ;;

    test-report)
        require_auth_env
        build_playwright_image
        configure_mock_api
        print_section "Running Playwright tests with live HTML report..."
        echo "Report will be served at http://localhost:9323 (press Ctrl+C to stop the viewer)."
        docker compose run --rm -p 9323:9323 playwright /bin/sh -c '
            npx playwright test;
            TEST_EXIT=$?;
            npx playwright show-report --host 0.0.0.0 --port 9323;
            exit $TEST_EXIT
        '
        ;;

    test-headed)
        require_auth_env
        build_playwright_image
        configure_mock_api
        print_section "Running Playwright tests in headed mode..."
        docker compose run --rm playwright npx playwright test --headed
        ;;

    test-debug)
        require_auth_env
        build_playwright_image
        configure_mock_api
        print_section "Running Playwright tests in debug mode..."
        docker compose run --rm playwright npx playwright test --debug
        ;;

    logs)
        SERVICE=${2:-guacamole-backend}
        require_auth_env
        validate_service "$SERVICE"
        print_section "Showing logs for $SERVICE..."
        docker compose logs -f "$SERVICE"
        ;;

    shell)
        SERVICE=${2:-guacamole-backend}
        require_auth_env
        validate_service "$SERVICE"
        print_section "Opening shell in $SERVICE..."
        docker compose exec "$SERVICE" /bin/sh
        ;;

    clean)
        require_auth_env
        print_section "Cleaning up test environment..."
        docker compose down -v --rmi local
        COMPOSE_STARTED=0
        rm -rf playwright/node_modules playwright/test-results playwright/screenshots/*.png
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;

    full)
        print_section "Provisioning Azure AD credentials..."
        scripts/setup-azure-auth.sh
        load_env_file
        require_auth_env
        APP_CREATED=1
        trap cleanup_all EXIT

        print_section "Building Guacamole Docker image..."
        cd ../guacamole-server
        docker build -f docker/Dockerfile -t guacamole-tre:latest .
        cd ../e2e-tests

        print_section "Starting test environment..."
        docker compose up -d
        COMPOSE_STARTED=1
        configure_mock_api

        build_playwright_image
        print_section "Running Playwright tests..."
        docker compose run --rm playwright npx playwright test

        print_section "Collecting screenshots..."
        mkdir -p ./playwright/screenshots
        docker compose cp playwright:/screenshots/. ./playwright/screenshots/ >/dev/null 2>&1 || true

        echo -e "${GREEN}✓ Full test suite complete${NC}"
        echo "Screenshots saved to: ./playwright/screenshots/"
        ;;

    help|*)
        echo "Usage: $0 {command}"
        echo
        echo "Commands:"
        echo "  build         - Build the Guacamole Docker image"
        echo "  up            - Start the test environment"
        echo "  down          - Stop the test environment"
        echo "  test          - Run Playwright tests"
        echo "  test-report   - Run tests and host the HTML report on http://localhost:9323"
        echo "  test-headed   - Run tests in headed mode (with browser UI)"
        echo "  test-debug    - Run tests in debug mode"
        echo "  logs [service] - Show logs for a service (default: guacamole-backend)"
        echo "  shell [service] - Open shell in a service (default: guacamole-backend)"
        echo "  clean         - Clean up all containers, volumes, and test artifacts"
        echo "  full          - Provision Azure auth, build image, run tests, and clean up"
        echo "  setup-auth    - Create Azure AD app registration and .env"
        echo "  help          - Show this help message"
        echo
        echo "Examples:"
        echo "  $0 full                # Run complete E2E test suite"
        echo "  $0 build && $0 up      # Build and start environment"
        echo "  $0 test                # Run tests"
        echo "  $0 logs guacamole-backend # View Guacamole logs"
        echo "  $0 clean               # Clean up everything"
        echo "  $0 setup-auth          # Provision Azure AD app and .env"
        ;;
esac

echo
