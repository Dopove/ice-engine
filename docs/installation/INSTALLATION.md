# 🚀 ICE Installation Guide

This guide covers setting up the ICE Engine and its dependencies.

## 1. Prerequisites
*   **PostgreSQL**: (Required) Used for the persistent memory ledger. Must have the `pgvector` extension enabled.
*   **Redis**: (Required) Used for high-speed caching and session management.

## 2. Environment Variables
ICE is configured via environment variables. Create a `.env` file in your project root or export them in your shell:
```bash
DATABASE_URL="postgres://user:pass@host/db"
REDIS_URL="redis://host:6379/0"
```

## 3. Python SDK Installation
```bash
# Install from PyPI
pip install ice-engine

# Or, install from source for development
pip install -e .
```

## 4. Node.js SDK Installation
```bash
# Install from npm
npm install @ICE Core Team/ice-client

# Or, install from source for development
cd clients/node/ice-client && npm install && npm run build
```

## 5. Starting the Engine
Once the package is installed and environment variables are set, you can start the engine via the CLI:
```bash
ice serve --host 0.0.0.0 --port 8008 --workers 4
```

## 6. Docker Compose Quickstart
For local development, we provide a `docker-compose.yml` that spins up the required PostgreSQL and Redis instances.
```bash
docker-compose up -d
```
You can then connect your ICE application to these local services.
