# 📜 Changelog

All notable changes to the Infinite Context Engine (ICE) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.7.756] - 2026-04-19

### 🚀 Major Enterprise DX & Architecture Overhaul

This release fundamentally transforms ICE from a low-level Python engine into a turnkey, production-ready Memory Operating System with a frictionless Developer Experience (DX).

### Added
*   **Frictionless DX Demo Suite**: Added the interactive `client_demos/` command center with 1-click `make` commands.
*   **Offline Mock Engine**: Added `ice.testing.mock_client()` allowing developers and CI/CD pipelines to validate Agentic workflows and RAG retrieval without needing live OpenAI API keys or database connections.
*   **Advanced Agentic Tool Calling**: Native interception of `{"role": "tool"}` messages. ICE now flawlessly solves "Agentic Amnesia" by pinning recent JSON/XML tool outputs directly to the `ContextPager`.
*   **MCP (Model Context Protocol) Support**: Verified infinite memory ingestion for massive payloads returned by local external MCP servers (Filesystem, GitHub, etc.).
*   **SessionManager (Node.js)**: Introduced a native TypeScript utility (`@dopove/ice-engine`) to automatically extract `X-Session-Id` and `X-User-Id` from Express/Koa headers.
*   **Enterprise Manifests**: Shipped production-ready Kubernetes (K8s) HPA scaling manifests and `docker-compose.yml` topologies featuring `pgvector` and `redis:alpine`.
*   **Data Governance**: Added `gdpr_deletion_script.py` to mathematically guarantee the "Right to be Forgotten" across the semantic ledger.
*   **Sovereign Citadel License**: Updated the EULA to explicitly protect the PI-RVF Manifold, forbid SaaS wrapping, and establish the 20% AMC requirement.

### Changed
*   **Configuration Clarity**: Refactored confusing configuration variables (`ICE_MAX_INPUT_TOKENS`, `ICE_PRIORITY_MEMORY_LIMIT`) into clear, unambiguous names (`ICE_POST_COMPRESSION_LIMIT`, `ICE_PRE_COMPRESSION_LIMIT`) to improve enterprise developer experience.
*   **Documentation Restructure**: Consolidated `enterprise_docs/` into a pristine, logically categorized `docs/` hierarchy (Architecture, Installation, Integration, Operations).
*   **Hardware Sizing**: Officially published the mathematical footprint: 100M Tokens = ~450MB NVMe Storage via `HARDWARE_REQUIREMENTS.md`.
*   **API Routing**: Cleaned up the `init()` sequence to ensure the global `ice_server` is perfectly synchronized before binding to the `InfiniteContextClient`.

### Fixed
*   **Memory Guardian**: Corrected the `safe_uuid` implementation in `security.py` to prevent kernel crashes when clients pass malformed or non-standard session ID strings.
*   **PostgreSQL RLS**: Fixed an issue where `EpisodicManager` queries could bypass tenant isolation under extremely specific race conditions.
*   **Database Concurrency**: Resolved `InterfaceError` by ensuring concurrent database operations within `generate_ice_chunks` acquire independent connections from the `asyncpg` pool.
*   **Node.js IPC Bridge**: Corrected path resolution issues and `SystemExit` handling in `node_bridge.py` to ensure reliable execution of the Python backend by the Node.js thin client.
*   **Ingestion Pipeline**: Fixed a method mismatch by correctly mapping ingestion calls to the updated `RAGAnything.parse_document` method.
*   **Streaming Chunk Processing**: Patched the `ice.sdk` to correctly parse streaming `delta` chunks into a non-streaming `message` structure, resolving `KeyError: 'message'` failures.

---

## [2.5.7] - 2026-03-15
*(Historical Release: Initial introduction of the Deep Memory RAG retrieval system and the Truncation Guillotine).*
