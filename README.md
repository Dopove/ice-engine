# 🧊 ICE: Infinite Context Engine
### Embedded Memory Operating System for AI Agents

ICE (Infinite Context Engine) is an open-source, high-performance library for providing AI agents with persistent, multi-modal, and horizontally scalable virtual memory. It integrates seamlessly into existing Python and Node.js applications to manage massive context windows efficiently.

---

## ⚡ Quick Start

### 1. Installation

**Python SDK:**
```bash
pip install ice-engine
```

**Node.js SDK:**
```bash
npm install @dopove/ice-client
```

### 2. The One-Import Mandate

Stop maintaining Redis, pgvector, and manual recall heuristics. ICE replaces all of it.

```python
from ice.sdk import init, get_client
```

That's it. ICE is a stateless SDK that hooks into your existing PostgreSQL and Redis clusters to provide infinite-memory capabilities.

---

## 🏗️ Architectural Pillars
- **Stateless Kernel**: ICE manages state in your existing databases, enabling horizontal pod scaling without session stickiness.
- **KV-Cache Alignment**: Recursive generation optimization reduces continuation overhead to sub-millisecond levels.
- **Vector-Graph Hybrid**: Stores episodic memory in a hybrid knowledge graph, combining semantic search (vectors) with relationship traversal (graphs).

## 🔌 Developer Integration
- [**Installation Guide**](docs/installation/INSTALLATION.md): Complete setup for Python and Node.js environments.
- [**Integration Guide**](docs/integration/DEVELOPER_EXPERIENCE.md): How to architect agents with ICE.
- [**Deployment Guide**](docs/DEPLOYMENT.md): Production Kubernetes/Docker patterns.

---
**(c) 2026 Infinite Context Engine (OSS)**
