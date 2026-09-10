---
type: subsystem
title: Multi-Tenant Security & Governance
description: SecurityManager's actual authentication surface versus what the admin CLI expects of it, plus data governance/purge, circuit breaking, rate limiting, and the billing usage-metering stub.
tags: [security, multi-tenancy, governance, gdpr, circuit-breaker, rate-limiting, billing]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-1cdb31194e7c0dd78de875b8
    resource: repo://ice/admin/cli.py
  - id: openwiki-source-7320d1471ea79a8c1f32d6fa
    resource: repo://ice/core/billing.py
  - id: openwiki-source-f0ee5b920dc27a9313f50184
    resource: repo://ice/core/episodic.py
  - id: openwiki-source-71cacfb421a7facad745f26c
    resource: repo://ice/core/governance.py
  - id: openwiki-source-13b0bd2ac9146ecc6d68785b
    resource: repo://ice/core/reasoning.py
  - id: openwiki-source-50b8ec8749f2936bf2bc4eaa
    resource: repo://ice/core/security.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Overview

"Security" in ICE spans several independent, loosely-coupled pieces: a minimal `SecurityManager` for request authentication, a standalone `governance.purge_data` function for tenant erasure, per-upstream `CircuitBreaker`s, a `TokenBucketRateLimiter`, and a `meter_usage` billing stub. There is no single access-control layer — each piece is invoked from a different call site (the gateway, the admin CLI, or a background loop).

## SecurityManager: what it actually implements

`ice/core/security.py`'s `SecurityManager` is intentionally minimal in this build:

```python
class SecurityManager:
    def __init__(self):
        self.enabled = os.getenv("ICE_ENABLE_AUTH", "true").lower() == "true"
    async def authenticate_request(self, request):
        if not self.enabled:
            ...
            return True
        return True  # no actual logic implemented
```

`authenticate_request` always returns `True` — whether or not `ICE_ENABLE_AUTH` is set, it does not currently reject anything. The real per-request tenant resolution and auth used by the gateway (`verify_tenant` in `ice/main.py`) does not call `SecurityManager` at all; it does its own Redis/Postgres/Secrets-Manager lookup directly (see [[gateway-api]]).

A separate module-level function, `verify_access_key`, is a simple boolean check (`bool(api_key)`, or `True` unconditionally if `ICE_DISABLE_AUTH=true`) that is not called from `ice/main.py`'s route dependency graph either — it exists as a standalone helper, not wired into the request path.

### Gap: `SecurityManager` has no tenant/API-key CRUD

`ice/admin/cli.py`'s tenant-management commands (`create_tenant`, `list_tenants`, `delete_tenant`, `generate_api_key`, `list_api_keys`, `revoke_api_key` — see [[admin-cli]]) call methods like `security.create_tenant(...)`, `security.get_tenant(...)`, `security.list_tenants()`, `security.generate_api_key(...)`, `security.revoke_api_key(...)` on a `SecurityManager()` instance. **None of these methods are defined on `SecurityManager`** — the class only has `__init__` and `authenticate_request`. Every admin CLI tenant/API-key command will raise `AttributeError` against the current implementation. Likewise, `export_telemetry`/`delete_telemetry` in the same CLI call `GET /v1/telemetry/export` and `DELETE /v1/telemetry/data`, neither of which exists as a route in `ice/main.py` (only `/v1/telemetry/status` and `/v1/telemetry/force-flush` are defined) — both commands will get a 404 from the FastAPI `TestClient`.

### Related gap: `SecurityManager.safe_uuid`

`EpisodicManager` and `ReasoningManager` (see [[episodic-memory]]) call `SecurityManager.safe_uuid(tenant_id)` as an (implied) static/class method before every SQL query involving `tenant_id`. This method is likewise **not defined anywhere in the codebase** — every episodic/reasoning database call in the current tree calls a method that does not exist on the class.

Actual per-tenant isolation in the running system today is enforced only by the `WHERE tenant_id = $1` clause built into each SQL query in `episodic.py`/`reasoning.py`/`governance.py` — i.e. tenant scoping happens at the query-construction level, not via a dedicated access-control abstraction.

## Data governance: `purge_data`

`ice/core/governance.py`'s `purge_data(tenant_id, user_id=None, db_pool=None)` is a standalone async function (not a method on any manager) that permanently `DELETE`s rows from `episodic_ledger` for a tenant (optionally scoped further to one `user_id`). It requires an explicit `db_pool` argument — it does not reach into `ice_server` globally — and raises `ValueError` if none is supplied. It reports the number of deleted rows by parsing the tail of the Postgres `DELETE` command tag (`"DELETE <n>"`). It is not called from `ice/main.py` or `ice/admin/cli.py` in this tree — no HTTP route or CLI command currently triggers it; a caller must invoke it directly, e.g. from a script or a future admin command. It is scoped only to `episodic_ledger` — it does not also purge `reasoning_traces`, unlike the retention-loop purges in `episodic.py`/`reasoning.py` which cover both tables (see [[episodic-memory]]).

## Circuit breaking and rate limiting

Full mechanics for `CircuitBreaker` (per-upstream, Redis-persisted, three-state) and `TokenBucketRateLimiter` (per-process, in-memory token bucket) are documented in [[gateway-api]], since both are instantiated and driven from `ICEServer`/`verify_tenant`. In summary for the security/governance angle: the circuit breaker protects *outbound* calls to upstream LLM providers (fail fast once a provider is unhealthy), while the rate limiter protects the gateway itself from being overwhelmed by a single tenant — neither is a tenant-isolation mechanism on its own.

## Billing: `meter_usage`

`ice/core/billing.py`'s `meter_usage(license_arn, tokens)` is an explicit placeholder — it only logs the metering event; the actual AWS License Manager `report_usage` call is commented out. It's invoked fire-and-forget (`asyncio.create_task`, not awaited) from `generate_ice_chunks` in `ice/main.py`, only when `ice_server.security` has a `license_arn` attribute set (which the current `SecurityManager.__init__` never sets) — so in practice this call path is present but its `hasattr` guard is never true with the stock `SecurityManager`, meaning usage metering does not currently fire even though the call site exists.

## License tiers

Despite the gaps above, license-tier limits are enforced structurally: `get_current_license_limits()` in `ice/main.py` reads `ice_server.security.license_payload` (if present) to determine per-SKU limits (`ICE-COMMUNITY`, `ICE-DEVELOPER-PRO`, or unlimited default), and those limits are actively enforced in `verify_tenant` (global tenant cap, with a hard-coded single-community-tenant rule) and `track_concurrent_session` (per-tenant concurrent session cap) — see [[gateway-api]] for both.
