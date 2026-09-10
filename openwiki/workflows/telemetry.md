---
type: subsystem
title: Telemetry & Observability Pipeline
description: The gateway's direct OTel SDK wiring versus the ice/telemetry/* package (RemoteTelemetryClient, TelemetryMiddleware, privacy redaction) — the latter fails to import in the current environment, and its privacy allowlist would drop nearly all payload content even if it did.
tags: [telemetry, opentelemetry, otlp, pii-redaction, privacy]
sources:
  - id: openwiki-source-d4364381e48f485694d35099
    resource: repo://docs/telemetry-setup.md
  - id: openwiki-source-0f62c624c73ee4a3ce3a9b4f
    resource: repo://ice/__init__.py
  - id: openwiki-source-171667cf123329a8f00acf34
    resource: repo://ice/kernel.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
  - id: openwiki-source-4816105a24dd8776719fca46
    resource: repo://ice/telemetry/__init__.py
  - id: openwiki-source-1b9df18f32db9dc5763bb75f
    resource: repo://ice/telemetry/config.py
  - id: openwiki-source-c874914d6f31ecec50ae3cd6
    resource: repo://ice/telemetry/emitter.py
  - id: openwiki-source-16e7fe594fd66b67c59cd2f3
    resource: repo://ice/telemetry/middleware.py
  - id: openwiki-source-06eef0a343de6ec42a965d03
    resource: repo://ice/telemetry/privacy.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
---

## Two telemetry code paths

1. **`ice/main.py`'s direct OTel SDK wiring** — trace/metric/log providers configured at module-import time, `FastAPIInstrumentor`/`prometheus-fastapi-instrumentator` auto-instrumenting every route. This is the gateway's actual, functioning request telemetry. See [[gateway-api]] for the full mechanics (resource attributes, sampler modes, `ErrorOnlySpanProcessor`, `/v1/telemetry/status`/`force-flush`).
2. **`ice/telemetry/*`** — a separate package (`TelemetryConfig`, `RemoteTelemetryClient`, `TelemetryMiddleware`, `privacy.py`) intended for SDK-embedded clients and/or richer FastAPI request telemetry, independent of path 1's module-level OTel providers.

`docs/telemetry-setup.md` documents both paths as if fully working; path 2 previously failed to import (see below — that's since been fixed).

## `RemoteTelemetryClient` no longer speaks custom HTTP, and now imports cleanly

An earlier version of `RemoteTelemetryClient` posted gzip JSON batches to a custom `/v1/telemetry/batch` HTTP route; that endpoint never existed on the server, and the client has since been rewritten (per its own docstring and `_send_batch`'s comment: "This replaces the former JSON-over-HTTP batch send to the now-removed /v1/telemetry/batch endpoint") to route telemetry through the OpenTelemetry SDK itself — `TelemetryConfig.endpoint` now defaults to `OTEL_EXPORTER_OTLP_ENDPOINT` (falling back to `http://localhost:4317`), matching the server-side OTLP contract described in [[gateway-api]] and [[operations/deployment-infrastructure]]. `docs/telemetry-setup.md` confirms this migration in its own text ("the legacy `ICE_TELEMETRY_ENDPOINT` / `/v1/telemetry/batch` HTTP route is no longer used by the client").

**`ice/telemetry/emitter.py` previously failed to import in this environment, and both underlying bugs are now fixed:**

- It imported `from opentelemetry.sdk._metrics import MeterProvider as SdkMeterProvider` and `from opentelemetry.sdk._metrics.export import PeriodicExportingMetricReader` — the private, underscore-prefixed `opentelemetry.sdk._metrics` module, which does not exist in the installed `opentelemetry-sdk` package (confirmed directly: `import opentelemetry.sdk._metrics` raises `ModuleNotFoundError`). Both imports now use the public, stable `opentelemetry.sdk.metrics` path (no underscore) — matching what `ice/main.py` itself has always imported from (`from opentelemetry.sdk.metrics import MeterProvider`, `PeriodicExportingMetricReader` — see [[gateway-api]]). Because `ice/telemetry/__init__.py` re-exports `RemoteTelemetryClient` from `emitter.py`, this had propagated to every module importing from `ice.telemetry` — including `ice/kernel.py` and `ice/admin/cli.py` — so `ICEKernel` construction now proceeds past this import to the separately-documented `SecurityManager(license_key)` mismatch (see [[architecture/overview]]), which is still broken.
- `_send_batch`'s metric branch called `get_meter_provider().get("ice.sdk.metrics")` to obtain a `Meter`. The standard `MeterProvider` API (consistent with `ice/main.py`'s own usage — `meter_provider.get_meter("ice-engine")`) exposes `get_meter(name, ...)`, not `.get(...)`. This call now reads `get_meter_provider().get_meter("ice.sdk.metrics")`.

## Privacy redaction defaults would drop nearly all payload content

`redact_pii` (`ice/telemetry/privacy.py`) applies, per key: skip if in `denied_attributes`; **skip if `allowed_attributes` is non-empty and the key isn't in it**; otherwise hash/anonymize/pattern-redact the value. `TelemetryConfig.allowed_attributes` defaults to `["service.name", "ice.version"]` — a two-item allowlist. Since this default list is non-empty, the "skip if not allowlisted" branch is active by default, and it drops every key not literally named `service.name` or `ice.version`. The payload shapes actually built by `TelemetryMiddleware` (`type`, `timestamp`, `method`, `path`, `status_code`, `duration_ms`, `request_size_bytes`, `response_size_bytes`, `tenant_id`, `session_id`, `user_agent` — see below) and by `RemoteTelemetryClient.emit_metric`/`emit_trace`/`emit_log` (`type`, `timestamp`, `name`, `value`, `labels`, `data`, `level`, `message`, `attributes`) contain none of those two keys — so with the library's own defaults, `redact_pii` reduces essentially every telemetry payload to an empty dict before it reaches `emit()`'s queue, independent of the `denied_attributes` list (which would otherwise only strip a handful of specifically-named sensitive fields like `user.email`/`prompt`/`authorization`). A caller must explicitly override `allowed_attributes` (e.g. to `[]`, meaning "no allowlist restriction") to get any payload content through under the default `pii_redaction=True`.

`hash_identifier`/`hash_ip`/`_redact_patterns` (SHA-256 truncated-hex hashing of `tenant_id`/`session_id`/`user_id`/`trace_id`/`span_id`; octet-preserving IP hashing; regex redaction for email/phone/SSN/credit-card/API-key/JWT/AWS-credential patterns) are all correctly implemented and would work as documented on any key that actually survives the allowlist filter above.

## `TelemetryMiddleware` — implemented, but not wired in, and needs manual assembly even if it were

`TelemetryMiddleware` (`ice/telemetry/middleware.py`) is a `BaseHTTPMiddleware` that measures request duration and size, extracts `tenant_id`/`session_id` from `X-Tenant-Id`/`X-Ice-Tenant-Id` and `X-Session-Id`/`X-Ice-Session-Id` headers (a different tenant-header convention than the gateway's own `verify_tenant`, which uses `Authorization: Bearer` + `X-Session-Id`/`X-User-Id` — see [[gateway-api]]), skips a fixed set of paths (`/health`, `/live`, `/ready`, `/metrics`, `/v1/telemetry`), and emits `http_request`/`http_error` payloads via an injected `telemetry_client.emit(...)`. As established in [[gateway-api]], nothing in `ice/main.py` constructs a `TelemetryMiddleware` or calls `app.add_middleware(TelemetryMiddleware, ...)` — it is dead code from the running gateway's perspective. Even if it were wired in, `__init__` requires an already-`start()`-ed `RemoteTelemetryClient` to be passed in explicitly (`telemetry_client=None` is the default, and the middleware silently no-ops — `return await call_next(request)` — whenever it's `None`); nothing in `ice/main.py` constructs and starts a `RemoteTelemetryClient` for this purpose either. Telemetry emission errors inside `_emit_request_telemetry`/`_emit_error_telemetry` are caught and silently swallowed (bare `except Exception: pass`), so a broken emitter would never surface as a request-level failure — consistent with the "don't let telemetry errors affect the request" design intent stated in the code.

## Docs reference server routes and an SDK entrypoint that don't exist

`docs/telemetry-setup.md`'s "Data Export (GDPR Compliance)" and "Data Deletion" sections document `GET /v1/telemetry/export` and `DELETE /v1/telemetry/data` as live server endpoints with example `curl` commands — matching what `ice/admin/cli.py`'s `export-telemetry`/`delete-telemetry` commands call (see [[admin-cli]]) — but neither route is defined in `ice/main.py` (only `/v1/telemetry/status` and `/v1/telemetry/force-flush` exist — see [[gateway-api]]). The docs' "Client SDK Integration → Python" example also shows `from ice import ICE` and `ICE(telemetry=TelemetryConfig(...))`, but `ice/__init__.py`'s public API exports only `init`, `get_client`, `IndexlessContextClient`, `MockClient`, and `purge_data` — there is no `ICE` class anywhere in the package.
