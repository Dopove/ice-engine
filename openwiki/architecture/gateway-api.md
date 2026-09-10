---
type: subsystem
title: FastAPI Gateway & Request Lifecycle
description: How ice/main.py's FastAPI app boots, authenticates and rate-limits requests, and dispatches OpenAI/Anthropic/Gemini-compatible chat requests through generate_ice_chunks.
tags: [fastapi, gateway, authentication, rate-limiting, circuit-breaker, opentelemetry, streaming]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
sources:
  - id: openwiki-source-8648e53fcd2abecc1ba4b766
    resource: repo://ice/core/circuit_breaker.py
  - id: openwiki-source-5a079267fa7d04ab0be3dc8a
    resource: repo://ice/core/rate_limit.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
---

## Overview

`ice/main.py` is the entire HTTP surface of ICE: a single ~1650-line FastAPI module that wires up OpenTelemetry, defines the `ICEServer` service container, authenticates requests, and exposes protocol-compatible routes for OpenAI, Anthropic, and Gemini clients — all funneling into one shared generation function, `generate_ice_chunks`.

## Module-load-time setup

Before the `FastAPI()` app object is even constructed, the module does all OpenTelemetry provider wiring at import time (not inside a startup hook):

- **Resource** (`build_resource`) — `service.name=ice-engine`, version from `ICE_VERSION`, `deployment.environment`, plus opportunistic K8s/cloud attributes from env vars, extensible via `ICE_OTEL_RESOURCE_ATTRIBUTES` (comma-separated `key=value`).
- **Sampler** (`build_sampler`, driven by `ICE_OTEL_SAMPLER`) — `error_only` (default; handled via a custom span processor, not a `Sampler`), `parent_based_always_on`, `traceidratio:<ratio>`, or `always_off`.
- **`ErrorOnlySpanProcessor`** — a `BatchSpanProcessor` subclass whose `on_end` drops any span that isn't `StatusCode.ERROR`, used when the sampler is `error_only` (the default) to cut outbound trace volume to just failures.
- **Metrics and logs** — `setup_metrics`/`setup_logs` build OTLP or console exporters the same way traces do, keyed off `OTEL_EXPORTER_OTLP_*` env vars, each independently overridable via a signal-specific endpoint var (`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `_METRICS_ENDPOINT`, `_LOGS_ENDPOINT`) that falls back to `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **Dual logging** — `root_logger.handlers` is replaced with exactly two handlers: `StructuredLogger` (writes NDJSON with `trace_id`/`span_id` to both stdout and `.logs/ice.log`) and the OTel `LoggingHandler`. Any handler configured elsewhere (e.g. by a library) is discarded.
- **`ice/telemetry/middleware.py`'s `TelemetryMiddleware` is never registered** on the FastAPI app — the gateway's only `app.middleware("http")` hook is `handle_server_state_middleware` (shutdown/degraded-mode signaling below). Request-level custom telemetry emission (redaction, custom span/metric shaping) described in [[telemetry]] is therefore currently dead code from the gateway's perspective; the gateway's actual request telemetry comes solely from `FastAPIInstrumentor.instrument_app` and `prometheus_fastapi_instrumentator`, both applied at the bottom of the module after every route is defined.

## `ICEServer`: the service container

A single `ICEServer` instance (`ice_server`, module-level global) owns all shared runtime state: `db_pool` (asyncpg), `redis`, `embedder`/`pager` (see [[native-context-engine]]), `reasoning`/`episodic` managers (see [[episodic-memory]]), `ingestion`, an `httpx.AsyncClient`, and four per-provider `CircuitBreaker` instances (`ollama`, `openai`, `anthropic`, `gemini`) plus one `TokenBucketRateLimiter`.

`ICEServer.startup()` (invoked from the FastAPI `startup` event):

1. Loads the native RCC core library via `get_lib()` — **this is a hard failure**: if the native library can't be loaded, `startup()` raises immediately, since "ICE V3 requires the Resonant C Compiler (RCC) core."
2. Determines RAG mode (`local` vs `external`) from the compiled `ice.build_config.RAG_MODE` if present, else `RAG_MODE` env var.
3. Before connecting Postgres, calls `setup_db.ensure_postgres_available()` (see [[database-provisioning]]) — checks connectivity and, unless `ICE_AUTO_PROVISION_DB=0`, offers to provision Postgres (Docker or native, developer's choice) if it's unreachable. If that still fails, it raises `RuntimeError`; connects Redis unconditionally. All of this is skipped entirely if `ICE_SKIP_INFRA_CONNECT=1`. **Any exception in this block — including that `RuntimeError` — is caught by the surrounding `except Exception as infra_err` and sets `self.degraded_mode = True` rather than propagating** — the gateway still intentionally boots in a degraded state instead of crashing when its datastores are unreachable, even after the new provisioning attempt fails. (Contrast [[architecture/overview]]'s `ICEKernel.connect()`, which has no such catch and does fail loudly.)
4. Re-verifies the embedder's ONNX session and tokenizer initialized; failure here also flips `degraded_mode`.

`handle_server_state_middleware` (registered as `@app.middleware("http")`) is the only global request gate: it rejects everything with `503` while `is_shutting_down` is set, and stamps `X-ICE-DEGRADED: true` on every response header while `ice_server.degraded_mode` is true (it does not block requests in degraded mode — routes individually decide how to behave, e.g. embeddings fall back to zero vectors).

Two background loops are started on startup: `retention_purge_loop` (every 24h, calls `episodic.purge_expired_ledger` + `reasoning.purge_expired_traces` concurrently) and `db_metrics_loop` (every 10s, publishes Postgres pool stats as Prometheus gauges).

## Authentication: `verify_tenant`

Every non-public route depends on `verify_tenant`, a `Header`-based FastAPI dependency (`Authorization: Bearer <api_key>`, optional `X-Session-Id`/`X-User-Id`). Resolution order:

1. **Redis fast path** — SHA-256 of the API key is looked up as `auth:key:<hash>`; a hit resolves `tenant_id` directly and applies rate limiting before returning.
2. **Postgres lookup** — `SELECT tenant_id FROM tenants WHERE api_key = $1`.
3. **AWS Secrets Manager fallback** — if `ICE_SECRET_ARN_PREFIX` is set and no DB row matched, a secret named `<prefix>/<api_key>` is fetched (off the event loop via `asyncio.to_thread`) and parsed for a `tenant_id`.
4. **New-tenant / dev-key path** — if still unresolved: the literal key `"ice-default-key"` with `ICE_ALLOW_DEFAULT_KEY=1` maps to a hardcoded default dev tenant UUID; otherwise a brand-new tenant row is created under the *server's own* SKU (`ICE_SKU`, default `ICE-DEVELOPMENT`), subject to `get_current_license_limits()`. An `ICE-COMMUNITY` server enforces a hard global cap of exactly one community tenant across the whole deployment.

A successful resolution always runs the shared `TokenBucketRateLimiter.consume(tenant_id)` before returning the auth context, and (outside degraded mode) caches the key→tenant mapping in Redis for 5 minutes.

Note: `verify_tenant` does not itself validate/normalize `tenant_id` as a UUID before later use — that responsibility sits with `SecurityManager.safe_uuid` calls inside `EpisodicManager`/`ReasoningManager` (see [[multi-tenant-security]]).

## Circuit breakers and rate limiting

`CircuitBreaker` (`ice/core/circuit_breaker.py`) is an async context manager with three states (0 closed, 1 open, 2 half-open) tracked per named upstream (`ollama_breaker`, `openai_breaker`, etc.). State optionally persists to Redis (`circuit_breaker:<name>`, 1h TTL) so it survives process restarts. Entering `__aenter__` while `failures >= failure_threshold` either re-opens to half-open (if `recovery_timeout` has elapsed) or raises `CircuitBreakerOpen` immediately; `__aexit__` resets failure count to 0 on success or increments it (and may trip to `open`) on any exception. Every state transition also updates the `ICE_CIRCUIT_BREAKER_STATE` Prometheus gauge, labeled by provider.

`TokenBucketRateLimiter` (`ice/core/rate_limit.py`) is a pure in-memory (not Redis-backed) token bucket keyed by an arbitrary string (tenant ID, or `"internal_search"` for the federated-search endpoint), refilled lazily on each `consume()` call based on elapsed wall-clock time — meaning bucket state is per-process and does not synchronize across multiple gateway replicas.

A separate concurrency gate, `track_concurrent_session` (an `asynccontextmanager`), enforces the license tier's `max_concurrent_sessions` using a Redis `INCR`/`DECR` counter per tenant (`active_sessions:<tenant_id>`), with a 1-hour TTL safety net against counter leaks from crashed processes; it's a no-op when Redis is unavailable or the tier has unlimited sessions.

## Routes

| Route | Purpose |
|---|---|
| `GET /`, `GET /v1` | Liveness-style status; returns 503 + "We're Hot as Lava" while `degraded_mode` |
| `GET /live` | Kubernetes liveness probe — always 200 if the process is up |
| `GET /ready` | Kubernetes readiness probe — checks live DB (`SELECT 1`) and Redis `PING` |
| `GET /v1/health` | Public health with memory-pressure detection (`ICE_MEMORY_CAP_GB`, warns at 90%) |
| `GET /v1/telemetry/status` | Reports current OTel exporter/sampler/endpoint configuration per signal |
| `POST /v1/telemetry/force-flush` | Force-flushes trace/metric/log providers, reports per-signal success |
| `POST /v1/internal/search` | Federated-search callee — gated by `verify_internal_api_key` (`X-Internal-Api-Key` header, compared to `ICE_INTERNAL_API_KEY`), not `verify_tenant`; hidden from OpenAPI schema |
| `POST /v1/ingest` | Document ingestion via the native RCC library, with explicit path-traversal defense (resolved path must stay under `ICE_UPLOAD_DIR`) |
| `WS /v1/ws/chat` | WebSocket chat — does its own manual `verify_tenant` call using the handshake payload (not the FastAPI dependency graph), since WebSocket routes can't use `Depends` on headers the same way |
| `POST /v1/chat/completions` | OpenAI-compatible chat completions (streaming and non-streaming) |
| `POST /v1/messages` | Anthropic Messages-API-compatible endpoint, translating request/response shape via the Anthropic provider adapter |
| `POST /v1beta/models/{model}:streamGenerateContent`, `POST /v1beta/models/{model}:generateContent` | Gemini-compatible endpoints |

All four LLM-facing routes (`chat/completions`, `messages`, the two Gemini routes) follow the same shape: translate the protocol-specific request into an internal OpenAI-style message list (using a provider adapter — see [[provider-adapters]] — for Anthropic/Gemini), call `generate_ice_chunks` inside `track_concurrent_session`, and either stream Server-Sent-Events chunks back in the caller's wire format or accumulate them into a single non-streaming response. A `dict` chunk containing an `"error"` key from `generate_ice_chunks` short-circuits the non-streaming paths into a `502` response.

## Instrumentation wiring

At the very bottom of the module, after every route is defined: `FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)` adds automatic request/response spans, and `Instrumentator().instrument(app).expose(app)` (from `prometheus-fastapi-instrumentator`) exposes a `/metrics` Prometheus endpoint and auto-instruments request latency/count. This is the primary source of per-request telemetry, since the custom `TelemetryMiddleware` package is not wired in (see above).
