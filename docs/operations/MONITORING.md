# 🩺 ICE v2.7.756: Operational Monitoring & Deep-System Access

This specification defines the protocols for monitoring the health of the ICE kernel, accessing the underlying semantic ledgers, and diagnosing connectivity failures in high-concurrency environments.

---

## 1. Observability Topography (Logs & Traces)

### 📍 Log Locations & Access
ICE utilizes a dual-path logging architecture to ensure audit persistence.
- **Structured Stdout**: Real-time JSON logs streamed directly to the process console.
- **Persistent Audit File**: Automatically archived at **`.logs/ice.log`**.

### 🔍 Reading Real-time Errors
To tail production logs and filter for critical kernel errors:
```bash
tail -f .logs/ice.log | grep '"level":"ERROR"'
```

---

## 2. Infrastructure Health & Connectivity

### 🛰️ Core Health Endpoint
- **URL**: Check SDK health method.
- **Response**: SDK methods will return JSON containing `usage_gb`, `memory_cap_gb`, and `status`.
- **Failure (503)**: Indicates **Degraded Mode**. ICE will operate in Degraded Mode but will not persist or recall memory if the database is unreachable.

### 🦙 Connectivity Handshakes
If the client receives a "reach Ollama but fails later" error, execute these diagnostic handshakes:
1.  **Direct Ping**: `curl http://localhost:11434/api/tags` (Verify Ollama is listening).
2.  **Kernel Ping**: Use the SDK to request models (Verify ICE can route to Ollama).

---

## 3. Database & pgvector Persistence Access

ICE stores billions of tokens across two primary PostgreSQL tables. You can access these manually for auditing or maintenance.

### 🐘 Connecting to the Ledger
```bash
# Connect via psql using your DATABASE_URL
psql $DATABASE_URL
```

### 📊 Querying Memory Density
```sql
-- Check total stored conversational fragments
SELECT count(*) FROM episodic_ledger;

-- Check total reasoning traces (CoT scratchpads)
SELECT count(*) FROM reasoning_traces;

-- Verify RLS (Row Level Security) status
SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'episodic_ledger';
```

---

## 4. Resource Guardrails (Prometheus Metrics)

Point your Prometheus/Grafana instance to `/metrics` to monitor these critical ICE physics:
*   `ice_resource_usage_bytes`: Current RAM footprint of the VMM.
*   `ice_stitch_semaphore_locked`: Number of active recursive synthesis tasks. If `> 9` for extended periods, increase `ICE_MAX_STITCH_CONCURRENCY`.

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com  
**(c) 2026 DOPOVE PRIVATE LIMITED**
