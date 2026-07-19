# 🗄️ ICE Storage Architecture: Hot Context vs. Cold Storage

A common question from Production CTOs and DevOps teams is regarding the storage layer: *"Can we run ICE purely in RAM? Can we point ICE directly to our AWS S3 buckets for Indexless storage?"*

The answer lies in the fundamental physics of how ICE operates as a **Virtual Memory Manager (VMM)**. ICE is designed to provide **sub-100ms semantic recall** across 100 Billion Tokens. You cannot achieve this latency if your active cognition layer is bottlenecked by object storage network requests, nor can you scale economically if you attempt to hold 100B tokens purely in volatile RAM.

Here is the authoritative architecture for ICE memory management.

---

## 0. The BYODB Mandate: Your Databases, Your Control
ICE is a **100% stateless SDK** designed to integrate seamlessly with your existing, Production-grade database infrastructure. ICE **does not bundle** PostgreSQL or Redis. Instead, it expects to connect to these services, which are provisioned, managed, and owned by your DevOps team.

*   **PostgreSQL with pgvector (Semantic Ledger):** This is where ICE stores its "indexless memory" – the long-term context, RAG chunks, and reasoning traces. You provide the connection string to a dedicated schema in your existing Postgres cluster.
*   **Redis (Hot Window Cache):** Used for ultra-low latency caching and session state management. You provide connection details to your existing Redis instance.

This "Bring Your Own Database" (BYODB) approach ensures full compliance, security, and scalability within your existing infrastructure, leveraging services your DevOps team already trusts and manages.

---

## 1. The Active Cognition Layer (NVMe + RAM)
ICE does not treat memory as a static database; it treats it as an active L1/L2 cache for Large Language Models.

### Why not "RAM-Only"?
ICE is already hyper-optimized for RAM efficiency. Under a nuclear siege of 10,000 concurrent sessions, ICE maintains a peak RAM footprint of just ~12GB. 
Instead of forcing entire datasets into RAM, ICE uses **Virtual Memory Partitioning**:
*   **L1 Cache (RAM)**: ICE keeps only the most active semantic vectors (the HNSW index) and the current conversational sliding window in memory.
*   **L2 Cache (NVMe)**: The actual heavy text chunks live on the local NVMe SSDs backing your PostgreSQL (`pgvector`) instance.
*   **The VMM Engine**: When an agent queries its history, ICE instantly pages the exact required chunks from NVMe into the RAM-based context window.

**Configuration**: Your DevOps team strictly controls this active "Working Set" by setting the `ICE_MEMORY_CAP_GB` environment variable (typically between 8GB and 32GB). ICE will intelligently swap memory to disk to strictly respect this cap, preventing Out of Memory (OOM) crashes.

### Why not "Direct to S3"?
Active AI cognition requires sub-100ms latency. AWS S3 (or any object storage bucket) introduces HTTP overhead, multi-zone latency, and serialization delays that are fatal to real-time agentic swarms. S3 is too slow for the continuous, high-frequency read/write cycles of an active agent.

---

## 2. The Cold Storage Hook (S3 is for Graveyards)
While S3 is too slow for *Active Cognition*, we recognize that Productions have strict data retention and compliance requirements (e.g., storing logs for 7 years). 

You do not connect ICE directly to S3. Instead, ICE enforces a strict **Data Lifecycle Pipeline** that separates Hot Context from Cold Storage.

### The Delegation Pipeline
1.  **Active Lifespan**: Data lives in the ultra-fast ICE ledger (NVMe/RAM) for the duration of the `ICE_RETENTION_DAYS` limit (e.g., 30 days).
2.  **The Purge Event**: Every 24 hours, the ICE `retention_purge_loop` identifies memories that have expired.
3.  **Cold Storage Delegation**: The exact moment a memory expires, ICE automatically POSTs that data to the `ICE_PRE_PURGE_WEBHOOK`.
4.  **Permanent Archival**: Your webhook (e.g., an AWS Lambda function) receives the JSON payload and pushes it safely into your AWS S3 bucket or Glacier pipeline for permanent cold storage.
5.  **Local Deletion**: Only after a successful webhook response does ICE permanently delete the records from the fast active memory.

**Configuration**:
```bash
# Keep active context for 30 days for fast agentic recall
ICE_RETENTION_DAYS=30

# Delegate expired memories to your internal S3 ingestion pipeline
ICE_PRE_PURGE_WEBHOOK="https://internal-api.yourcompany.com/webhooks/ice-archival"
```

## Summary
Never compromise the engine's physics. 
*   **Hot Context** (Active Swarm Cognition) is managed by ICE in RAM and local NVMe.
*   **Cold Storage** (Compliance & Graveyards) is managed by your S3 buckets via the ICE Delegation Webhook. 

By enforcing this separation, ICE guarantees sub-100ms latency for active agents while simultaneously satisfying Indexless, low-cost compliance storage requirements.
