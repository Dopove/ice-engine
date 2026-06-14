# ⚙️ ICE Engine Configuration Reference

This document outlines the runtime environment variables available to DevOps engineers for tuning ICE. These variables can be passed directly via the CLI, an `.env` file, Docker Compose, or a Kubernetes ConfigMap.

## 1. Scaling & Resource Management

| Variable | Default | Description |
|----------|---------|-------------|
| `ICE_PORT` | `8000` | The port the ICE Engine binds to. |
| `ICE_MEMORY_CAP_GB` | `30.0` | Target memory threshold for context operations. |
| `ICE_MAX_STITCH_CONCURRENCY` | `10` | Maximum number of concurrent long-context operations allowed per node to prevent resource exhaustion. |
| `ICE_WORKERS` | `1` | Number of parallel worker processes. Recommended: 1 per 4 CPU cores. |
| `ICE_DB_MIN_POOL` | `5` | Minimum PostgreSQL connection pool size. |
| `ICE_DB_MAX_POOL` | `20` | Maximum PostgreSQL connection pool size. |

## 2. Context & RAG Orchestration

| Variable | Default | Description |
|----------|---------|-------------|
| `ICE_MODEL_CONTEXT_WINDOW` | `8192` | Total token limit (input + output). |
| `ICE_POST_COMPRESSION_LIMIT` | `8192` | The maximum context size passed to the underlying LLM per request. |
| `ICE_DEFAULT_OUTPUT_TOKENS` | `1024` | Default token generation budget if not explicitly requested by the client. |
| `ICE_MAX_CONTINUATIONS` | `10` | Maximum number of recursive stitching loops/turns for long-context generation. |
| `ICE_DYNAMIC_OUTPUT_BUDGET` | `true` | Toggles intelligent intent-based token budgeting. |
| `ICE_CHUNK_SIZE` | `8000` | Target chunk size (in characters) for document semantic partitioning. |
| `ICE_CHUNK_OVERLAP` | `500` | Character overlap during chunking to prevent data loss. |
| `ICE_STITCH_TAIL_CHARS` | `2000` | Size of the continuity window maintained during extended generations. |

## 3. Compliance & Retention

| Variable | Default | Description |
|----------|---------|-------------|
| `ICE_RETENTION_DAYS` | `30` | Number of days data is retained before automatic deletion. |
| `ICE_PRE_PURGE_WEBHOOK_URL` | `None` | (Optional) Endpoint to POST data to before it is purged from the database. Useful for cold-storage compliance. |
| `ICE_RAG_ENABLE_COMPLIANCE`| `false` | Enables PII redaction and compliance scrubbing on ingested documents. |
| `ICE_RAG_COMPLIANCE_LEVEL` | `standard` | Aggressiveness of PII redaction (`standard`, `strict`, `paranoid`). |

## 4. Multi-Modal Pipeline

| Variable | Default | Description |
|----------|---------|-------------|
| `ICE_RAG_PARSER` | `docling` | Document parsing engine (e.g., docling, mineru). |
| `ICE_RAG_ENABLE_IMAGES` | `true` | Process images and diagrams in uploaded documents. |
| `ICE_RAG_ENABLE_TABLES` | `true` | Extract and process complex tables. |
| `ICE_RAG_ENABLE_EQUATIONS` | `true` | Extract and process LaTeX/mathematical equations. |
| `ICE_UPLOAD_DIR` | `./uploads` | Sandboxed directory for RAG file ingestion. Prevents path traversal vulnerabilities. |

## 5. Security & Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `ICE_SECRET_KEY` | `default-dev-secret-key-12345` | Cryptographic secret for signing offline JWT licenses and hardware seals. |
| `ICE_STRICT_DRM` | `0` | If `1`, triggers physical deletion of proprietary core modules upon license failure or forgery. |
| `ICE_ALLOW_DEFAULT_KEY` | `0` | If `1`, allows the use of `ice-default-key` for bypassing authentication (dev environments only). |
| `ICE_SECRET_ARN_PREFIX` | `None` | AWS Secrets Manager prefix for mapping API keys to Tenant IDs. |
| `ICE_REDIS_SALT` | `default-ice-salt-2026` | Salt for generating unguessable Redis indexes in external telemetry mode. |
| `ICE_TELEMETRY_ENABLED` | `true` | Toggles internal OpenTelemetry and observability spans. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `None` | Endpoint for OTLP trace export (e.g., for Jaeger/Datadog). |

## 6. Routing & Models

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTREAM_API_URL` | `http://localhost:11434/v1/chat/completions` | Base URL for the upstream LLM (e.g., local Ollama). |
| `OPENAI_API_URL` | `https://api.openai.com/v1/chat/completions` | Routing destination for `gpt-` model requests. |
| `OPENAI_API_KEY` | `None` | API key for OpenAI routing. |
| `ANTHROPIC_API_URL`| `https://api.anthropic.com/v1/messages` | Routing destination for `claude-` model requests. |
| `ANTHROPIC_API_KEY`| `None` | API key for Anthropic routing. |

## 7. Infrastructure Connections

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgres://ice_user:ice_password@localhost:5432/ice_db` | PostgreSQL connection string for episodic ledger. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string for hot-context caching and auth. |
| `RAGX_REDIS_HOST` | `redis://localhost:6379/1` | Redis connection string specifically for external RAG indices. |
| `RAGX_REDIS_ADMIN_HOST` | `None` | Admin host for Redis configuration. |
| `RAGX_REDIS_ADMIN_USER` | `default` | Admin user for configuring Redis ACLs dynamically. |
| `RAGX_REDIS_ADMIN_PASSWORD` | `None` | Admin password for Redis ACL configuration. |
| `REDIS_ACL_PASS_<USER>` | `None` | Password for specific Redis ACL users (dynamic mapping). |

---

## 🏗️ Deployment Examples

### Docker Compose Example
You can pass these variables directly into your `docker-compose.yml` file under the `environment` section:

```yaml
services:
  ice-engine:
    image: dopove/ice-enterprise:v2.7.756
    environment:
      # Resource Management
      - ICE_MEMORY_CAP_GB=64.0
      - ICE_MAX_STITCH_CONCURRENCY=20
      - ICE_WORKERS=8
      
      # Context Tuning
      - ICE_POST_COMPRESSION_LIMIT=16384
      - ICE_MAX_CONTINUATIONS=15
      
      # Enterprise Compliance
      - ICE_RETENTION_DAYS=365
      - ICE_PRE_PURGE_WEBHOOK_URL=https://hooks.yourdomain.com/ice-archive
      - ICE_RAG_ENABLE_COMPLIANCE=true
      - ICE_RAG_COMPLIANCE_LEVEL=strict
      
      # Security
      - ICE_SECRET_KEY=super-secret-crypto-key
      - ICE_STRICT_DRM=1
```

### Kubernetes ConfigMap Example

In Kubernetes, it is best practice to manage these non-sensitive variables via a `ConfigMap`.

Create an `ice-configmap.yaml` file:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ice-config
data:
  # Resource Management
  ICE_MEMORY_CAP_GB: "64.0"
  ICE_MAX_STITCH_CONCURRENCY: "20"
  ICE_WORKERS: "8"
  ICE_DB_MIN_POOL: "10"
  ICE_DB_MAX_POOL: "50"
  
  # Context Tuning
  ICE_POST_COMPRESSION_LIMIT: "16384"
  ICE_MAX_CONTINUATIONS: "15"
  ICE_CHUNK_SIZE: "8000"
  
  # Enterprise Compliance
  ICE_RETENTION_DAYS: "365"
  ICE_PRE_PURGE_WEBHOOK_URL: "https://hooks.yourdomain.com/ice-archive"
  ICE_RAG_ENABLE_COMPLIANCE: "true"
  ICE_RAG_COMPLIANCE_LEVEL: "strict"
  
  # Multimodal Settings
  ICE_RAG_ENABLE_IMAGES: "true"
  ICE_RAG_ENABLE_TABLES: "true"
  ICE_UPLOAD_DIR: "/app/uploads"
```

Apply the ConfigMap to your cluster:
```bash
kubectl apply -f ice-configmap.yaml
```

Ensure your `Deployment` references this ConfigMap:
```yaml
        envFrom:
        - configMapRef:
            name: ice-config
```