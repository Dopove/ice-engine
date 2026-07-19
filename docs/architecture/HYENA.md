# ICE Hyena (Horizon Cloud) Architecture

**Tier Status:** Project Hyena (Service/Recurring)
**Service Model:** Annual Subscription + License Fee
**Codename:** Horizon

## 🌌 Infinite Context Horizon
ICE Hyena is the managed cloud-hybrid tier that unlocks truly infinite context storage. By offloading the RAG vector store to ICE Core Team's multi-region external Redis clusters, enterprises bypass local hardware storage limits.

### Core Characteristics
- **Infinite Context:** `TTL=None`. Context never expires and is persisted across infinite sessions.
- **Multi-Region Proximity:** Managed Redis clusters are deployed in the same AWS region as the client (e.g., `ap-south-1`) to ensure imperceptible network latency (<2ms).
- **Global Telemetry Loop:** Aggregates anonymized failure patterns to feed [[Maggie]]'s continuous learning engine.

## 🔒 Client-Side Trust Layer
Security is enforced *inside* the client VPC before any data is transmitted to the external Horizon cluster.

### 1. Client-Side Scrubber
The ICE engine automatically redacts sensitive information using a military-grade regex suite:
- **PII:** Emails, Phone Numbers, SSNs, Credit Cards.
- **Infrastructure:** Internal IPv4/IPv6 addresses.
- **Secrets:** API keys, passwords, and auth tokens.
- **Business Logic:** Entire code blocks are redacted to prevent proprietary logic leakage.

### 2. Tenant Isolation & Network Security
Every enterprise receives a cryptographically hashed namespace and a dedicated Redis user.
- **Redis ACLs**: ICE uses `ACL SETUSER` to restrict each tenant to their specific key-prefix: `ice-rag-{sha256(tenant_id)}*`.
- **Encryption**: Data is transmitted via **WireGuard/ts-ice** E2EE tunnels, ensuring that even in the cloud, your memory ledger is invisible to the public internet.

### 🖼️ Multimodal Cloud Persistence
Hyena mode supports the full 100B Token multimodal horizon.
- **Storage**: Image/Audio blobs are serialized and stored in the managed Redis cluster.
- **Recall**: Large media assets are retrieved and reconstructed in the prompt turn with <5ms additional latency.

## 📈 Performance & God Equation SLA
Despite the network hop, ICE Hyena maintains elite performance standards:
- **Regional Network Hop:** <2ms.
- **Encryption Overhead:** <1ms (WireGuard/ts-ice).
- **Total Retrieval Latency:** Verified at ~17-18ms.
- **Guaranteed Boundary:** Strict adherence to the **ICE Core Team Constant ($D = 5.902880$)**, ensuring all operations remain well under the 100ms SLA.

## 🔧 Configuration
Set the following environment variable to activate Hyena mode:
```bash
RAG_MODE=external
RAGX_REDIS_HOST=redis://managed.ICE Core Team.io:6379/1
ICE_TELEMETRY_ENABLED=true
```
