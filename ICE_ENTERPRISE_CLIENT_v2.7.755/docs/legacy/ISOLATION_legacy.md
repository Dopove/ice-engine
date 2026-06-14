# ICE Isolation & Security: The Fortress
## Zero-Trust Data Architecture

### Kernel-Level PostgreSQL RLS
ICE enforces multi-tenancy at the lowest possible layer. Every database transaction is wrapped in a tenant-specific scope:
`SET LOCAL ice.current_tenant_id = <X-User-ID>;`
This prevents cross-tenant data leakage even in the event of an application-layer breach.

### 🛡️ Dual-Layer Memory Isolation
1.  **Episodic Ledger**: Isolated by PostgreSQL RLS. Semantic search only retrieves vectors belonging to the authorized `tenant_id` and `user_id`.
2.  **Reasoning Ledger**: Internal chain-of-thought traces are stored in a separate table, preventing CoT leakage into the primary chat history of other users.

### 🔐 Multi-Tenant Redis ACLs (Hyena Mode)
In cloud-hybrid deployments, ICE dynamically generates unique Redis users for each tenant. 
*   **Access Control**: Each tenant is restricted to a specific hashed key-prefix (`ice-rag-{hashed_tenant}*`).
*   **Protocol**: ICE uses `ACL SETUSER` during initialization to enforce these boundaries at the network layer.

### Hardware-Bound Licensing
The `ICE_LICENSE_JWT` is cryptographically bound to the host `CPU-ID`. Verification is performed against the **AWS License Manager** in real-time.

### The Kill Switch Warning
If the system detects a license mismatch, hardware tampering, or unauthorized `X-User-ID` access patterns, the **Integrated Kill Switch** will engage, immediately wiping transient KV-Caches and halting all Engine transactions to protect intellectual property and sensitive data.

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com
**(c) 2026 DOPOVE PRIVATE LIMITED**
