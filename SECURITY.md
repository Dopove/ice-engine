# 🛡️ Enterprise Security & Compliance (SECURITY.md)

DOPOVE PRIVATE LIMITED is committed to the absolute security and cryptographic integrity of the Infinite Context Engine (ICE). 

This document outlines our security posture, vulnerability disclosure policy, and compliance standards for Enterprise and Sovereign deployments.

---

## 1. Compliance & Certifications

The ICE Kernel is engineered to support the strictest global regulatory frameworks:

*   **SOC 2 Type II Compliance**: ICE provides native telemetry (`ICE_TELEMETRY_ENABLED`), Row-Level Security (RLS) isolation, and immutable audit logging to support your internal SOC 2 audits.
*   **GDPR & CCPA**: The engine includes a native Data Governance utility (`gdpr_deletion_script.py`) to execute cryptographic, hard SQL deletions of specific users across the 100B Token Horizon to satisfy "Right to be Forgotten" requests.
*   **HIPAA & PCI-DSS**: The `ICE_RAG_ENABLE_COMPLIANCE=true` flag activates the Financial Security Tier, scrubbing PII, PANs, and PHI from unstructured documents before they are embedded into the Semantic Ledger.

## 2. Software Supply Chain Security

Enterprise procurement requires absolute transparency into our software supply chain.

*   **SBOM (Software Bill of Materials)**: A signed CycloneDX SBOM is generated and attached to every ICE release. This guarantees that all upstream dependencies (e.g., `fastapi`, `asyncpg`, `pgvector`) are free of critical CVEs prior to distribution.
*   **Binary Hardening**: The Python `.whl` and Node.js `.node` C++ distributions are compiled using proprietary obfuscation and stripped of all debug symbols to prevent reverse engineering and intellectual property theft.

## 3. Vulnerability Disclosure Policy (VDP)

If you discover a security vulnerability in the ICE Engine, the Semantic Ledger integration, or the hardware-locking mechanisms, please report it immediately.

**DO NOT open a public GitHub issue.**

### Reporting a Vulnerability
Please email your findings to **security@dopove.com**. 
Include the following:
1. The ICE version (e.g., v2.7.756).
2. A detailed description of the vulnerability.
3. A Proof of Concept (PoC) script or steps to reproduce.

### Response Time (SLA)
*   **Acknowledgment**: Within 12 hours.
*   **Triage & Severity Assessment**: Within 48 hours.
*   **P0/Critical Patch Release**: Within 72 hours.

## 4. Data Privacy & Liability

**ICE is a self-hosted product that runs exclusively within your Virtual Private Cloud (VPC) or on-premise infrastructure.** This architecture is fundamental to our security posture and your data sovereignty.

*   **Zero PII / Raw Data Collection**: Dopove Private Limited collects **zero raw data or Personally Identifiable Information (PII)** from your ICE instances. The only information we receive is anonymized performance telemetry (e.g., query speed, cache hit rate) when `ICE_TELEMETRY_ENABLED` is active, which is used for performance tuning and critical support.
*   **Client Liability**: Because the software and all associated data (including the Semantic Ledger in PostgreSQL) operate entirely within your controlled environment, **you are 100% liable for your own data security and breaches**. It is your responsibility to secure your cloud infrastructure, databases, and network access according to industry best practices.

---

## 5. Hardware Seal Architecture

The ICE binary enforces licensing via a cryptographic hardware seal bound to the host CPU-ID and MAC address. 
*   **Air-Gapped Environments**: Once the initial JWT signature is validated via the AWS License Manager, the generated `license.ice` seal permits 100% offline, air-gapped execution for high-security Sovereign deployments (e.g., Defense, Intelligence, Healthcare).
*   **Anti-Tamper**: Any attempt to manipulate the system clock, clone the VM state, or spoof the MAC address will trigger the **Self-Defending Protocol**, cryptographically locking the binary and invoking `exit(137)`.
