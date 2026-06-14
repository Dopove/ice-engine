# ⚙️ ICE v2.7.756: Exhaustive Customization Reference (Staff-Engineer Grade)

This specification defines the absolute runtime thresholds for the **ICE v2.7.756** engine. Every variable is exposed via environment injection, allowing for precise alignment with enterprise infrastructure without exposing proprietary machine code.

**Universal Storage Backend**: As of this release, ICE supports universal storage backends. You can ingest documents directly from local paths (`./my-docs`), AWS S3 (`s3://my-bucket/docs`), or Google Cloud Storage (`gcs://my-bucket/docs`) by providing the full URI to the `ice.ingest()` method. The engine will use standard cloud credentials (e.g., `~/.aws/credentials` or `GOOGLE_APPLICATION_CREDENTIALS`). Azure Blob Storage is explicitly not supported.

---

## 1. System Scaling & Memory Governance

| Variable | Default | Technical Impact | Tuning Strategy |
| :--- | :--- | :--- | :--- |
| `ICE_MEMORY_CAP_GB` | `30.0` | Threshold for the **Memory Guardian**. | Increase for 64GB+ VRAM nodes. |
| `ICE_MAX_STITCH_CONCURRENCY`| `10` | Caps simultaneous synthesis tasks. | Prevents KV-Cache thrashing. |
| `ICE_WORKERS` | `4` | Number of parallel processing units. | `1 per 4 CPU cores` recommended. |

## 2. Persistence Layer (PostgreSQL + Redis)

| Variable | Default | Function | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `postgres://...` | Connection to the **Semantic Ledger**. | Required for Long-term Recall. |
| `REDIS_URL` | `redis://...` | Connection to **Hot Window Cache**. | Required for sub-10ms state sync. |
| `ICE_DB_MIN_POOL` | `5` | Min asyncpg connection pool. | Baseline latency protection. |
| `ICE_DB_MAX_POOL` | `20` | Max asyncpg connection pool. | Scale for 10,000+ sessions. |
| `ICE_RETENTION_DAYS` | `30` | **Data Lifecycle Policy**. | Set to `2555` for 7-year compliance. |
| `ICE_PRE_PURGE_WEBHOOK` | `None` | Cold Storage Delegation URL. | Archive data before deletion. |

## 3. Intelligence & Budgeting (Memory Physics)

| Variable | Default | Technical Description |
| :--- | :--- | :--- |
| `ICE_POST_COMPRESSION_LIMIT` | `128000` | Total virtual context budget allowed per inference turn. |
| `ICE_CHUNK_SIZE` | `12000` | Character count per semantic partition. |
| `ICE_CHUNK_OVERLAP` | `1000` | Buffer overlap to prevent symbol fragmentation in codebases. |
| `ICE_MAX_CONTINUATIONS` | `100` | Absolute turn-limit for the Recursive Output engine. |
| `ICE_PRE_COMPRESSION_LIMIT`| `5` | Number of recent tool results "pinned" to the prompt. |
| `ICE_REASONING_RECALL_LIMIT`| `10` | Max traces retrieved from the Reasoning Ledger. |
| `ICE_RAG_CONFIG_FILE`| `None` | Path to a JSON file for deep multimodal customization (OCR resolution, table strategies, etc.). |

## 4. Provider Routing & Safety

| Variable | Default | Technical Impact |
| :--- | :--- | :--- |
| `UPSTREAM_API_URL` | `http://localhost:11434`| Routing target for local **Ollama** models. |
| `OPENAI_API_URL` | `https://api.openai.com`| Global routing for GPT-tier swarms. |
| `ANTHROPIC_API_URL` | `https://api.anthropic.com`| Routing for Claude Messages API. |
| `GEMINI_API_URL` | `https://generativelanguage...`| Routing for Google Gemini-CLI. |
| `ICE_ALLOW_DEFAULT_KEY` | `false` | Bypasses multi-tenant RLS for local dev. |

---
**Security Warning**: ICE implementations include a **Self-Defending Protocol**. Unauthorized binary execution on unverified hardware will result in an immediate `SIGKILL` and cryptographic erasure of the local activation seal.

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com  
**(c) 2026 DOPOVE PRIVATE LIMITED**
