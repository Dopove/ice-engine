---
type: guide
title: ICE Quickstart & Task Routing
description: What ICE is, how to actually boot it in this tree today, and which wiki page covers which system.
tags: [quickstart, overview, task-routing]
sources:
  - id: openwiki-source-164e2da859b5277df81c7d94
    resource: repo://.github/workflows/ci.yml
  - id: openwiki-source-f011a030ad13c406633402c0
    resource: repo://docker-compose.test.yml
  - id: openwiki-source-c6ad3edea88b91e6531f91d7
    resource: repo://ice/cli.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
---

## What ICE is

ICE ("Indexless Context Engine") is a proxy/middleware layer that sits between an application and an upstream LLM provider (OpenAI, Anthropic, Google, or local Ollama), retrieving and injecting relevant conversation history into each request so the model behaves as if it has unbounded memory — without the caller managing a vector database or chunking logic. Start at [[architecture/overview]] for the full picture of how the pieces fit together.

## The three ways to consume ICE, and which one actually works today

ICE exposes three consumption surfaces, but they are not equally functional in this tree:

1. **HTTP Gateway** (`ice.main:app`, run via `ice serve`, `uvicorn ice.main:app`, or the Docker image) — a standalone FastAPI process any OpenAI/Anthropic/Gemini-compatible client can call. **This is the surface that actually works** — see [[architecture/gateway-api]] for its routes and request lifecycle.
2. **In-process SDK** (`await ice.sdk.init(...)`) — still broken at construction: `ICEKernel.__init__` calls `SecurityManager(license_key)` with an argument that constructor doesn't accept. The earlier import-time failure (`ice.telemetry` importing a private OpenTelemetry module path that didn't exist) has been fixed, so construction now gets further before failing — but it still fails, at the `SecurityManager` call. See [[architecture/overview]] and [[workflows/sdk-and-clients]].
3. **Drop-in wrapper** (`ICEWrapper(existing_client)`, `ice/wrapper.py`) — needs no ICE server or kernel at all; wraps an already-constructed OpenAI/Anthropic SDK client and intercepts `.chat.completions.create(...)` to inject/save memories via a local DuckDB store. This is the lightest-weight path and doesn't depend on the broken kernel construction. See [[workflows/sdk-and-clients]].

The registered `ice` console script (`ice/cli.py`, `pyproject.toml`'s `[project.scripts]`) previously couldn't even be imported — it imported a `license_cli` module that never existed in the repo. That's been removed, so `ice` now works: `ice serve` (launch the gateway), `ice mount` (SDK-backed ingestion — still broken, since it goes through the SDK path above), `ice help`, `ice db update` (ensure Postgres is reachable — offering Docker or a native install if not, see [[operations/database-provisioning]] — then apply the schema), and `ice self-update`. See [[operations/gateway-cli]]. The tenant-management admin CLI (`ice/admin/cli.py`) is a separate, still-unregistered command group with its own set of construction failures — see [[operations/admin-cli]].

**Practical path to booting locally:** `ice serve` (or `uvicorn ice.main:app --host 0.0.0.0 --port 8000`), first running `ice db update` if you don't already have Postgres reachable at `DATABASE_URL` — it'll offer to provision one via Docker or your OS package manager. For a dependency-free smoke test with no database at all, set `ICE_SKIP_INFRA_CONNECT=1` and `ICE_MOCK_LLM_CALL=1` (this is exactly what the CI integration-tests job and `docker-compose.test.yml` do — see [[testing/testing-strategy]]).

## Task routing — which page covers what

| If you're working on... | Read |
|---|---|
| Overall system shape, how the gateway/SDK/wrapper paths differ | [[architecture/overview]] |
| FastAPI routes, request auth, rate limiting, circuit breakers | [[architecture/gateway-api]] |
| Prompt assembly, token budgeting, the native C library, embeddings | [[architecture/native-context-engine]] |
| Chat history persistence/search, reasoning traces, PII scrubbing | [[architecture/episodic-memory]] |
| Tenant auth gaps, data governance/purge, billing metering | [[architecture/multi-tenant-security]] |
| Translating Anthropic/Gemini requests, upstream provider dispatch | [[architecture/provider-adapters]] |
| Multimodal document ingestion, the external RAG mirror, local storage | [[workflows/ingestion-and-rag]] |
| OTel wiring, the `ice/telemetry/*` package, PII redaction defaults | [[workflows/telemetry]] |
| The Python SDK, the drop-in wrapper, the Node.js bridge/native addon | [[workflows/sdk-and-clients]] |
| Tenant/API-key CLI commands | [[operations/admin-cli]] |
| The `ice` console script: serve, mount, help, db update, self-update | [[operations/gateway-cli]] |
| Postgres auto-provisioning (Docker vs. native, interactive choice) | [[operations/database-provisioning]] |
| Terraform/AWS deployment, ECS/ADOT collector, CloudWatch, Docker | [[operations/deployment-infrastructure]] |
| Test suite structure, CI pipeline, the Docker-gate/CI mismatch | [[testing/testing-strategy]] |

## A note on this wiki's tone

This codebase has a substantial gap between what several modules' names/docstrings/README claim and what their code currently does — mismatched method names across files, imports of Python/library modules that don't exist in the pinned dependency versions, and infrastructure config with resource-schema errors. Every such gap documented across this wiki was verified directly against the source (and, where possible, against the actually-installed dependency versions) rather than inferred from comments or docs — see each page's own "gap"/"defect" callouts for specifics and file:line evidence.
