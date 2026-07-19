# 📊 ICE Hardware Requirements & Memory Retention Benchmarks

This document provides empirical telemetry data from the ICE Engine stress tests and establishes the hardware requirements for Production Production deployments.

---

## 1. Empirical Benchmark Results (v3.1.75)

The following metrics were captured during active stress-testing of the ICE Engine running on a standard development node (16GB RAM, 8-Core CPU). Note that ICE acts as a **Embedded Engine** and **Virtual Memory Manager (VMM)**; actual LLM inference occurs upstream.

### Test A: The 1,000 Concurrent Request Siege
*Simulates a DDoS-level event or massive swarm booting simultaneously. Validates the `STITCH_SEMAPHORE` queue stability.*
*   **Concurrency**: 1000 simultaneous massive-generation requests.
*   **Completion Time**: 10.53 seconds
*   **Peak CPU Usage**: 15.2% - 21.8%
*   **Peak RAM Usage**: 9.1 GB (remained strictly clamped by `ICE_MEMORY_CAP_GB`)
*   **Active VRAM**: ~8 MB (Engine overhead only)
*   **Queue Status**: 10 Active / 990 Waiting -> Processed flawlessly without OOM (Out of Memory).

### Test B: Mixed Workload Stress (Chat, Agents, Tools)
*Simulates a production environment mixing standard chat, structured JSON data extraction, and multi-turn agentic workflows.*
*   **Concurrency**: 30 sustained heavy workflows.
*   **Peak CPU Usage**: 20.4% - 25.0%
*   **Peak RAM Usage**: 8.9 GB
*   **Disk I/O**: High read/write throughput during Semantic Ledger paging operations.

---

## 2. Memory Retention Physics

ICE provides a **100-Billion Token Virtual Context Window**. 
To understand the hardware impact, we must look at how ICE stores data.

*   **1 Token** ≈ 4 bytes of text.
*   **100 Million Tokens** ≈ 400 MB of raw text.
*   **Embedding Vectors**: A 384-dimensional vector (e.g., from `all-MiniLM-L6-v2`) requires ~1.5 KB per chunk.

**Retention Efficiency**:
Because ICE chunks data (default `ICE_CHUNK_SIZE=12000` chars, ~3000 tokens) and embeds each chunk, a 100-Million token user session requires approximately:
*   **Text Storage**: ~400 MB
*   **Vector Index (pgvector)**: ~50 MB
*   **Total DB Footprint per 100M Tokens**: ~450 MB

---

## 3. Production Production Estimates

For a SaaS platform or Production deployment expecting **10,000 Active Users**, with each user consuming roughly **10 Million Tokens of history**:

### A. ICE Engine Nodes (Kubernetes / Docker)
The ICE Engine is completely stateless. It scales horizontally.
*   **Minimum Setup**: 3 Replicas (Pods)
*   **Per-Node Specs**: 
    *   **CPU**: 4 - 8 Cores (High clock speed preferred for semantic assembly)
    *   **RAM**: 16 GB - 32 GB (Set `ICE_MEMORY_CAP_GB=24.0`)
    *   **Disk**: 50 GB NVMe (For local OS and temporary multimodal chunking)

### B. Semantic Ledger (PostgreSQL + pgvector)
This is the heart of the "Infinite Context" engine. 
*10,000 users * 10M tokens = 100 Billion Tokens.*
*   **Database Size Required**: ~450 GB to 500 GB
*   **Hardware Specs**:
    *   **CPU**: 16 - 32 Cores (Critical for fast HNSW vector index lookups)
    *   **RAM**: 64 GB - 128 GB (To keep the HNSW index fully in memory for sub-10ms recall)
    *   **Storage**: 1 TB NVMe SSD (High IOPS is mandatory for fast retrieval).

### C. Hot-Context Cache (Redis)
Used for transient session mapping, rate limiting, and Cloud-Tier cloud buffering.
*   **RAM**: 16 GB - 32 GB (Standard Redis requirements)

---

## 4. Hardware Optimization Strategies

1.  **Restrict Maximum Concurrency (`ICE_MAX_STITCH_CONCURRENCY`)**: 
    If your engine RAM is limited to 8GB, set this to `4`. ICE will gracefully queue requests instead of crashing with an Out of Memory (OOM) error.
2.  **Smart Retention (`ICE_RETENTION_DAYS`)**:
    Set the retention policy to 30 or 90 days. The nightly `retention_purge_loop` will automatically drop old rows from PostgreSQL, keeping your disk costs predictable.
3.  **Local Embedding (`EmbeddingModel`)**:
    ICE runs the ONNX embedding model entirely on the CPU by default. For a 2x-3x speedup on ingestion, provision the engine nodes with entry-level GPUs (e.g., NVIDIA T4 or L4) and enable ONNX GPU execution providers.

---
**ICE Engine Contributors**  | [github.com/ice-engine](https://www.github.com/ice-engine/) | community@ice-engine.org  
**(c) 2026 ICE Engine Contributors**
