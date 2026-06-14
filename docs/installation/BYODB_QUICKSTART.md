# 🚀 BYODB Quickstart: Connecting ICE to Your Existing Databases

The Infinite Context Engine (ICE) is a **100% stateless SDK** designed to integrate seamlessly with your existing, enterprise-grade database infrastructure. ICE **does not bundle** PostgreSQL or Redis in its deployments. Instead, it expects to connect to these services, which are provisioned, managed, and owned by your DevOps team.

This "Bring Your Own Database" (BYODB) approach ensures full compliance, security, and scalability within your existing infrastructure, leveraging services your DevOps team already trusts and manages.

---

## 1. Prerequisites (Your Responsibility)

Before integrating ICE, ensure you have:

*   **Production-Grade PostgreSQL Instance:** This should be a highly available, managed PostgreSQL cluster (e.g., AWS RDS, Azure Database for PostgreSQL, Google Cloud SQL, or a self-hosted Kubernetes operator).
*   **`pgvector` Extension:** Your PostgreSQL instance must have the `pgvector` extension enabled.
*   **Production-Grade Redis Instance:** This should be a highly available, managed Redis cluster (e.g., AWS ElastiCache, Azure Cache for Redis, or a self-hosted solution).

---

## 2. Database Preparation

ICE requires a dedicated space within your existing PostgreSQL and Redis infrastructure.

### 2.1. PostgreSQL (Semantic Ledger)

ICE needs a dedicated database or schema within your PostgreSQL cluster to store its Semantic Ledger (infinite memory, RAG chunks, reasoning traces).

1.  **Create a Database or Schema:**
    ```sql
    -- Option A: Create a new database (recommended for isolation)
    CREATE DATABASE ice_semantic_ledger;

    -- Option B: Create a new schema within an existing database
    -- CREATE SCHEMA ice_schema;
    ```
2.  **Enable `pgvector` Extension:**
    Connect to your chosen database/schema and enable the `pgvector` extension.
    ```sql
    -- Connect to your new or existing database, then:
    CREATE EXTENSION IF NOT EXISTS vector;
    ```
    *(Your DBA team can typically enable extensions in minutes.)*

### 2.2. Redis (Hot Window Cache)

ICE uses Redis for ultra-low latency caching and session state. It will use a dedicated set of keys (prefixed with `ice:`) within your existing Redis instance. No specific setup is required other than providing a connection string.

---
## 3. Configuring ICE with Your Databases

You provide ICE with the connection strings via standard environment variables.

### 3.1. Production Environment

In a production environment (like Kubernetes), you would inject these as secrets.

```bash
# Example: AWS RDS Postgres
export DATABASE_URL="postgresql://<user>:<password>@<your-rds-endpoint>:5432/ice_semantic_ledger"

# Example: AWS ElastiCache Redis
export REDIS_URL="redis://<your-elasticache-endpoint>:6379"
```

### 3.2. Local Development Environment

For local development and testing, you can use the `docker-compose.yml` file provided in `client_demos/deployment/docker/`. The default connection strings for this local setup are:

```bash
# Default local development connection strings
export DATABASE_URL="postgres://ice_user:ice_password@localhost:5433/ice_db"
export REDIS_URL="redis://localhost:6379/0"
```

---

## 4. Degraded Mode (No Database Connection)

**Is the database configuration optional?**

Yes. If `DATABASE_URL` and `REDIS_URL` are not provided, ICE will automatically enter a **stateless, in-memory mode**.

*   **Behavior:** In this mode, ICE functions as a simple context window manager. It will not persist any memory between requests. If a conversation exceeds the `max_input_tokens` limit, it will fall back to basic **head-and-tail truncation** (keeping the first few and last few messages).
*   **Use Case:** This mode is useful for lightweight development, quick testing of prompts, or scenarios where persistent memory is not required. It is **not recommended for production use** as it disables ICE's core infinite memory and RAG capabilities.

---

## 5. Automatic Schema Migration
```python
import os
import asyncio
from ice.sdk import init, get_client

async def main():
    ice_client = await init(
        # ICE will automatically read DATABASE_URL and REDIS_URL from environment variables
        # or you can pass them directly:
        # database_url=os.getenv("DATABASE_URL"),
        # redis_url=os.getenv("REDIS_URL"),

        # Other configurations...
        max_input_tokens=128000,
        license_key=os.getenv("ICE_LICENSE_JWT")
    )
    print("ICE Kernel initialized and connected to your databases!")
    # Your application logic here...

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2. Initialization (Node.js SDK)

```typescript
import { IceClient } from '@dopove/ice-node';
import * as process from 'process';

const ice = new IceClient({
    // ICE will automatically read DATABASE_URL and REDIS_URL from environment variables
    // or you can pass them directly via an advanced config object if needed.
    // For environment variables, ensure they are set before starting your Node.js app.
    licenseJwt: process.env.ICE_LICENSE_JWT || "your-enterprise-license-jwt"
});

async function runDemo() {
    console.log("ICE Client initialized and ready to connect to your databases!");
    // Your application logic here...
}

runDemo();
```

---

## 4. Automatic Schema Migration

When the ICE Kernel initializes, it automatically performs necessary schema migrations (e.g., creating the `episodic_ledger` table, `active_nodes` table, and ensuring `pgvector` is initialized) in the PostgreSQL database you provide. This ensures that ICE is always ready to store and retrieve memory without manual database setup.

---

## 5. Deployment Considerations

In Kubernetes, you would manage `DATABASE_URL` and `REDIS_URL` using **Secrets** (for sensitive credentials) and **ConfigMaps** (for non-sensitive configuration) or a combination thereof, ensuring these are injected as environment variables into your application pods.
