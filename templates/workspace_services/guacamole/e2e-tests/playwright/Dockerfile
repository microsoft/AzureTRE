FROM mcr.microsoft.com/playwright:v1.56.1-noble

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (disable strict SSL for environments with self-signed certs)
RUN npm config set strict-ssl false && npm ci && npm config set strict-ssl true

# Copy test files
COPY . .

# Run tests
CMD ["npx", "playwright", "test"]
