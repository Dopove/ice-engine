---
type: overview
title: System Architecture Overview
description: The overall shape of ICE — the FastAPI gateway process versus the in-process SDK/kernel path, how they diverge, and how a request flows end to end through prompt assembly and upstream dispatch.
tags: [architecture, overview, fastapi, sdk, kernel, entrypoints]
sources:
  - id: openwiki-source-50b8ec8749f2936bf2bc4eaa
    resource: repo://ice/core/security.py
  - id: openwiki-source-171667cf123329a8f00acf34
    resource: repo://ice/kernel.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
  - id: openwiki-source-ecda5ab2a5d26aabcc134de4
    resource: repo://ice/sdk.py
  - id: openwiki-source-c874914d6f31ecec50ae3cd6
    resource: repo://ice/telemetry/emitter.py
  - id: openwiki-source-75d0e846003d86a50fbd4ca8
    resource: repo://ice/wrapper.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
---

## What ICE is

ICE ("Indexless Context Engine") is a proxy layer that sits between an application and an upstream LLM provider (OpenAI, Anthropic, Google, or a local Ollama model), automatically retrieving and injecting relevant past conversation history into each request so the upstream model behaves as if it has unbounded memory, without the caller managing a vector database or chunking logic themselves.

Two consumption models exist side by side in this codebase, and they are **not built from the same object graph**:

1. **HTTP Gateway** (`ice/main.py`) — a standalone FastAPI process (`ice.main:app`) that any OpenAI/Anthropic/Gemini-compatible client can call over HTTP or WebSocket. See [[gateway-api]].
2. **In-process SDK** (`ice/sdk.py` + `ice/kernel.py`) — a Python library (`await ice.init()`, `ice.get_client().chat.completions.create(...)`) for embedding ICE directly inside another Python application. See [[sdk-and-clients]].

## Two independently-constructed service containers

Both consumption paths need the same core managers (`EpisodicManager`, `ReasoningManager`, `IngestionPipeline`, `ContextPager`/`EmbeddingModel`, `SecurityManager`) — but each path constructs its own copy rather than sharing one:

- The gateway builds `ICEServer` (`ice/main.py`), instantiating each manager directly in `__init__`/`startup()`.
- The SDK builds `ICEKernel` (`ice/kernel.py`), which does the equivalent wiring independently.

**These two container classes are not interchangeable, and the `ICEKernel` path is currently broken at construction.** `ICEKernel.__init__` imports `from .telemetry import TelemetryConfig, RemoteTelemetryClient` (that import now succeeds — see [[telemetry]]) and then calls `self.security = SecurityManager(license_key)` — passing a positional `license_key` argument — but `SecurityManager.__init__(self)` (in `ice/core/security.py`) takes no arguments besides `self`. It also calls `self.security.verify_or_exit()` immediately afterward, and later `self.security.register_node()` in `connect()`; neither method exists on `SecurityManager` (which only implements `__init__` and `authenticate_request` — see [[multi-tenant-security]]). Constructing an `ICEKernel` — and therefore calling `ice.sdk.init()`, the SDK's documented entrypoint — still raises `TypeError` immediately, now specifically at the `SecurityManager(license_key)` call rather than at the (now-fixed) telemetry import.

If that constructor mismatch were fixed, `ICEKernel.connect()` would next call `setup_db.ensure_postgres_available()` (see [[database-provisioning]]) before opening its `asyncpg` pool — and, unlike `ICEServer.startup()` (see [[gateway-api]]), `connect()` has no surrounding exception handler, so a still-unreachable Postgres here raises `RuntimeError` straight out of `connect()` rather than falling back to a degraded mode.

The gateway's `ICEServer`, by contrast, never touches `SecurityManager` for tenant resolution at all — `verify_tenant` in `ice/main.py` does its own Redis/Postgres/Secrets-Manager lookup inline (see [[gateway-api]]) — so the gateway process boots and serves requests independently of the broken `ICEKernel`/`SecurityManager` coupling.

## Request flow (gateway path)

1. A client sends an OpenAI-, Anthropic-, or Gemini-shaped request to one of the protocol-compatible routes in `ice/main.py`.
2. `verify_tenant` resolves the caller's tenant identity and applies rate limiting (see [[gateway-api]]).
3. The route normalizes the request into an internal OpenAI-style message list (via a provider adapter for non-OpenAI shapes — see [[provider-adapters]]) and calls the shared `generate_ice_chunks`.
4. `generate_ice_chunks` embeds the latest user message (`get_cached_embedding`, Redis-cached), retrieves relevant history via `EpisodicManager.search_episodic` and active reasoning via `ReasoningManager.get_active_chain` (see [[episodic-memory]]), and assembles a single synthetic prompt via `ContextPager.assemble_prompt` (see [[native-context-engine]] — this is the pure-Python path; the native C library is not used here despite its presence).
5. The assembled prompt is dispatched to the resolved upstream provider through the matching `CircuitBreaker` (see [[gateway-api]]).
6. The response is saved back into `episodic_ledger` via `EpisodicManager.save_message`, streamed or accumulated back to the caller in the caller's wire format, and OpenTelemetry/Prometheus instrumentation records the turn.

## Request flow (SDK path, as designed)

`ice/sdk.py`'s `IndexlessContextClient.chat.completions.create(...)` is intended to be a thinner façade over the *same* `generate_ice_chunks` function used by the gateway (it imports `generate_ice_chunks` directly from `ice.main`), rather than reimplementing generation logic — but it hardcodes a single fixed `tenant_id` (`NATIVE_TENANT_ID`, a constant UUID) for every SDK-embedded caller, meaning the SDK path does not support multiple tenants the way the gateway does; all SDK-driven traffic within one process is attributed to one tenant. It also emits its own telemetry events (`chat_completion`, `ingest`) through `kernel.telemetry` (a `RemoteTelemetryClient` — see [[telemetry]]) in addition to whatever OTel spans `generate_ice_chunks` itself creates.

Note: `CompletionsInterface.create` and `IndexlessContextClient._emit_telemetry` call `time.time()`, but `ice/sdk.py` never imports the `time` module — every call to `client.chat.completions.create(...)` will raise `NameError: name 'time' is not defined` as currently written.

`IndexlessContextClient` also defines `ingest` twice (identical signature); Python keeps only the second definition, so the first — which lacks the `_emit_telemetry` call the second one has — is dead code, silently shadowed.

## Drop-in wrapper: `ICEWrapper`

A third, even thinner entry point, `ice/wrapper.py`'s `ICEWrapper`, doesn't talk to `ICEServer`/`ICEKernel` at all — it wraps an *existing* OpenAI/Anthropic SDK client object via `__getattr__` proxying, intercepting only `.chat.completions.create(...)` calls to inject retrieved memories (via a `MemoryStore`/`MemoryPolicy` pair, not the `EpisodicManager` used by the other two paths) into the outgoing message list, and to save the response afterward. This is the "3-line drop-in" pattern advertised in the README — it requires no ICE server or kernel process at all, trading the richer retrieval/reasoning pipeline for a much smaller integration footprint. See [[sdk-and-clients]] for details.

## Native library dependency

Regardless of which path is used, the gateway process (`ICEServer.startup()`) hard-fails at boot if the native `ice_core` shared library can't be loaded — even though, as detailed in [[native-context-engine]], that library's own prompt-assembly function isn't actually used by the request-handling hot path; only its (stubbed, no-op) `rcc_ingest_document` function is called, from the `/v1/ingest` route.
