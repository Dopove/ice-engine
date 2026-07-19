# ICE Local-Tier (Fortress Local) Architecture

**Tier Status:** Project Mammoth (Local/Isolated)
**Service Model:** One-Time Perpetual License
**Codename:** The Fortress

## 🛡️ Zero-Trust Data Local-Tierty
ICE Local-Tier is the air-gapped, high-security tier designed for Productions that require absolute data isolation. All context storage, retrieval, and inference operations occur strictly within the client's Virtual Private Cloud (VPC).

### Core Characteristics
- **Air-Gapped Execution:** Zero external network calls. No telemetry is transmitted to ICE Core Team servers.
- **Hardware Binding:** The ICE binary is cryptographically locked to physical CPU-IDs via the AWS License Manager (or equivalent hardware seal).
- **Local RAG Stack:** Utilizes a dedicated PostgreSQL/pgvector instance and local Redis for episodic and reasoning traces.

## 💾 Storage & Lifecycle Management
Unlike the cloud tier, storage in Local-Tier mode is limited by local hardware capacity. DevOps teams are responsible for provisioning and maintaining the storage layer.

- **Retention Policy:** Controlled via `ICE_RETENTION_DAYS`.
- **Garbage Collection:** Data is systematically purged after the retention period to prevent Out-of-Memory (OOM) failures on local NVMe drives.
- **Pre-Purge Archiving:** Supports `ICE_PRE_PURGE_WEBHOOK_URL` to offload data to cold storage (S3/Glacier) before permanent deletion.

## ⚡ Performance & SLA
- **Semantic Recall:** ~15ms (Native Engine Speed).
- **Stitching Overhead:** <1ms.
- **God Equation Compliance:** Guaranteed <100ms latency across the hardware-bounded context window.

## 🔧 Configuration
Set the following environment variable to activate Local-Tier mode:
```bash
RAG_MODE=local
ICE_TELEMETRY_ENABLED=false
```
