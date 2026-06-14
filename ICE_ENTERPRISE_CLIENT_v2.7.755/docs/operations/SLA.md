# 🤝 Service Level Agreement (SLA) & Support

This Service Level Agreement (SLA) defines the operational guarantees, uptime commitments, and support matrices provided by **DOPOVE PRIVATE LIMITED** to Enterprise clients utilizing the Infinite Context Engine (ICE) v2.6.x.

---

## 1. Uptime Guarantees (Hyena Cloud-Hybrid Tier)

For clients utilizing the **ICE Hyena** managed cloud tier (where Dopove manages the multi-region external Redis clusters and Vector Storage), we guarantee the following:

| Service Component | Guaranteed Uptime |
| :--- | :--- |
| **ICE Core API Engine** | 99.99% |
| **Managed Redis (Hot Cache)** | 99.99% |
| **Managed Semantic Ledger** | 99.95% |

### 1.1 SLA Credits
If Dopove fails to meet the 99.99% uptime guarantee in a given billing month, the Enterprise is entitled to service credits applied to their Annual Maintenance Contract (AMC):
*   **< 99.99% but ≥ 99.90%**: 10% Credit
*   **< 99.90% but ≥ 99.00%**: 25% Credit
*   **< 99.00%**: 50% Credit

*(Note: Uptime guarantees do not apply to Sovereign/On-Premise deployments where the client manages the hardware, networking, and database infrastructure).*

---

## 2. Performance SLA (The God Equation)

Dopove legally guarantees the physics of the ICE Kernel via the **Dopove Constant ($D = 5.902880$)**.

Assuming the client meets the Minimum Hardware Stipulations (NVMe SSDs, 32GB+ RAM):
*   **Maximum Semantic Recall Latency**: < 50ms (from the 100B Token Horizon).
*   **Maximum Stitching Overhead**: < 2ms (per recursive turn).
*   **Total ICE Overhead**: < 100ms added to the upstream LLM's Time-To-First-Token (TTFT).

If ICE overhead consistently exceeds 100ms under standard load, it is classified as a **P1 Incident**.

---

## 3. Incident Support Matrix

Access to the Enterprise Support Matrix requires an active 20% Annual Maintenance Contract (AMC). 
All tickets must be filed via the secure Dopove Enterprise Portal.

| Severity Level | Definition | Target Response Time | Target Resolution Time |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | Complete Engine failure; massive data corruption; total production outage affecting all users. | **< 30 Minutes** | Continuous 24/7 effort until resolved. |
| **P1 (High)** | Severe performance degradation (>100ms overhead); continuous `OOMKilled` crashes; specific tool integrations failing. | **< 2 Hours** | < 24 Hours |
| **P2 (Medium)** | Minor bug impacting a non-critical feature; RAG parsing errors on specific obscure PDF formats. | **< 12 Hours** | Next patch release |
| **P3 (Low)** | General architectural questions; onboarding assistance; documentation requests. | **< 24 Hours** | As needed |

## 4. End-of-Life (EOL) Policy

*   **Major Versions** (e.g., v2.x to v3.x) are supported for **24 months** after the release of the subsequent major version.
*   **Security Patches** for critical CVEs are backported to all supported major versions within 72 hours of triage.
