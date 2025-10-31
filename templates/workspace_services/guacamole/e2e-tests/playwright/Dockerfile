FROM mcr.microsoft.com/playwright:v1.49.1-noble

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy test files
COPY . .

# Run tests
CMD ["npx", "playwright", "test"]
