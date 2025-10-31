#!/bin/bash
# Guacamole E2E Test Runner
# This script simplifies running the end-to-end tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Parse command line arguments
COMMAND=${1:-help}

case "$COMMAND" in
    build)
        print_section "Building Guacamole Docker image..."
        cd ../guacamole-server
        docker build -f docker/Dockerfile -t guacamole-tre:latest .
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;
    
    up)
        print_section "Starting test environment..."
        docker-compose up -d
        echo
        echo -e "${GREEN}✓ Environment started${NC}"
        echo
        echo "Services running:"
        docker-compose ps
        ;;
    
    down)
        print_section "Stopping test environment..."
        docker-compose down
        echo -e "${GREEN}✓ Environment stopped${NC}"
        ;;
    
    test)
        print_section "Running Playwright tests..."
        docker-compose run --rm playwright npx playwright test
        ;;
    
    test-headed)
        print_section "Running Playwright tests in headed mode..."
        docker-compose run --rm playwright npx playwright test --headed
        ;;
    
    test-debug)
        print_section "Running Playwright tests in debug mode..."
        docker-compose run --rm playwright npx playwright test --debug
        ;;
    
    logs)
        SERVICE=${2:-guacamole}
        print_section "Showing logs for $SERVICE..."
        docker-compose logs -f "$SERVICE"
        ;;
    
    shell)
        SERVICE=${2:-guacamole}
        print_section "Opening shell in $SERVICE..."
        docker-compose exec "$SERVICE" /bin/sh
        ;;
    
    clean)
        print_section "Cleaning up test environment..."
        docker-compose down -v --rmi local
        rm -rf playwright/node_modules playwright/test-results playwright/screenshots/*.png
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
    
    full)
        print_section "Running full test suite..."
        echo "Step 1: Building Docker image..."
        cd ../guacamole-server
        docker build -f docker/Dockerfile -t guacamole-tre:latest .
        cd ../e2e-tests
        
        echo
        echo "Step 2: Starting environment..."
        docker-compose up -d
        
        echo
        echo "Step 3: Waiting for services to be ready..."
        sleep 10
        
        echo
        echo "Step 4: Running tests..."
        docker-compose run --rm playwright npx playwright test
        
        echo
        echo "Step 5: Collecting screenshots..."
        docker-compose cp playwright:/screenshots/. ./playwright/screenshots/
        
        echo
        echo -e "${GREEN}✓ Full test suite complete${NC}"
        echo
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
        echo "  test-headed   - Run tests in headed mode (with browser UI)"
        echo "  test-debug    - Run tests in debug mode"
        echo "  logs [service] - Show logs for a service (default: guacamole)"
        echo "  shell [service] - Open shell in a service (default: guacamole)"
        echo "  clean         - Clean up all containers, volumes, and test artifacts"
        echo "  full          - Run complete test suite (build + test + screenshots)"
        echo "  help          - Show this help message"
        echo
        echo "Examples:"
        echo "  $0 full                # Run complete E2E test suite"
        echo "  $0 build && $0 up      # Build and start environment"
        echo "  $0 test                # Run tests"
        echo "  $0 logs guacamole      # View Guacamole logs"
        echo "  $0 clean               # Clean up everything"
        ;;
esac

echo
