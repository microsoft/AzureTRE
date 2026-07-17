ARG PLAYWRIGHT_TAG=v1.56.1-noble
ARG PLAYWRIGHT_BASE_IMAGE=mcr.microsoft.com/playwright
FROM ${PLAYWRIGHT_BASE_IMAGE}:${PLAYWRIGHT_TAG}

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

RUN npm install

# Copy Playwright project files (tests live under ./tests)
COPY . .

# Run tests
CMD ["npx", "playwright", "test"]

