#!/bin/bash
set -e

echo "🚀 Setting up Guacamole development environment..."

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Install Playwright system dependencies
echo "🎭 Installing Playwright system dependencies..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libwayland-client0

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Build Java extension if in guacamole-auth-azure directory
if [ -d "guacamole-server/guacamole-auth-azure" ]; then
    echo "☕ Building Guacamole TRE authentication extension..."
    cd guacamole-server/guacamole-auth-azure
    mvn clean install -DskipTests
    cd ../..
fi

# Install Playwright dependencies if package.json exists
if [ -d "e2e-tests/playwright" ]; then
    echo "🎭 Installing Playwright and dependencies..."
    cd e2e-tests/playwright
    npm install
    npx playwright install chromium
    cd ../..
fi

# Set up git hooks
echo "🔧 Configuring git..."
git config --global --add safe.directory /workspaces/*

# Create useful aliases
echo "📝 Creating helpful aliases..."
cat << 'EOF' >> ~/.bashrc

# Guacamole development aliases
alias mvn-build='cd guacamole-server/guacamole-auth-azure && mvn clean install'
alias mvn-test='cd guacamole-server/guacamole-auth-azure && mvn test'
alias e2e-build='cd e2e-tests && docker-compose build'
alias e2e-up='cd e2e-tests && docker-compose up -d'
alias e2e-down='cd e2e-tests && docker-compose down'
alias e2e-test='cd e2e-tests/playwright && npm test'
alias e2e-ui='cd e2e-tests/playwright && npm run test:ui'
alias e2e-logs='cd e2e-tests && docker-compose logs -f'

# Show helpful commands on login
guac-help() {
    echo "🧪 Guacamole Development Commands:"
    echo "  mvn-build    - Build Java authentication extension"
    echo "  mvn-test     - Run Java unit and integration tests"
    echo "  e2e-build    - Build E2E test Docker containers"
    echo "  e2e-up       - Start E2E test environment"
    echo "  e2e-down     - Stop E2E test environment"
    echo "  e2e-test     - Run Playwright E2E tests (headless)"
    echo "  e2e-ui       - Run Playwright E2E tests (UI mode)"
    echo "  e2e-logs     - Show E2E environment logs"
    echo ""
    echo "📚 Quick Start:"
    echo "  1. mvn-build      # Build the extension"
    echo "  2. e2e-build      # Build test containers"
    echo "  3. e2e-up         # Start test environment"
    echo "  4. e2e-test       # Run E2E tests"
    echo ""
    echo "🌐 Ports:"
    echo "  8080 - Guacamole Web Interface"
    echo "  3000 - Mock TRE API"
    echo "  4200 - Playwright UI Mode"
}

EOF

echo "✅ Development environment setup complete!"
echo ""
echo "Run 'guac-help' for available commands and quick start guide."
