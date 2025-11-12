FROM mcr.microsoft.com/playwright:v1.56.1-noble

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

RUN npm install

# Copy test files
COPY . .

# Run tests
CMD ["npx", "playwright", "test"]
