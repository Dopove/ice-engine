---
type: operations
title: Admin CLI & Tenant Management
description: ice/admin/cli.py's tenant, API-key, and telemetry management commands, how to invoke them, and why every command that touches the kernel or SecurityManager currently fails against the rest of the tree.
tags: [admin-cli, tenant-management, api-keys, gdpr, click]
sources:
  - id: openwiki-source-1cdb31194e7c0dd78de875b8
    resource: repo://ice/admin/cli.py
  - id: openwiki-source-c6ad3edea88b91e6531f91d7
    resource: repo://ice/cli.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-9fe3a610596da7b7f2c71115
    resource: repo://setup.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
---

## Invocation

`ice/admin/cli.py` defines a `click` command group (`cli`, exposed as `main()`) covering tenant lifecycle, API key management, GDPR-style telemetry export/delete, and server bootstrap. **It is not registered as a console script** — neither `pyproject.toml`'s `[project.scripts]` nor `setup.py`'s `entry_points` define anything beyond `ice = ice.cli:main`, which is a separate, smaller CLI (`ice serve`, `ice mount`, `ice license`) defined in `ice/cli.py`. To run the admin CLI in this tree, invoke it directly: `python -m ice.admin.cli <command>` or import and call `main()` from `ice/admin/cli.py`.

(Separately, `ice/cli.py` — the CLI that *is* registered as the `ice` console script — previously imported `from .license_cli import license`, a module that never existed in this tree, so importing `ice.cli` raised `ModuleNotFoundError` before any of its commands could run. That import has since been removed; `ice/cli.py` now imports and runs cleanly, with its own `serve`/`mount`/`help`/`db update`/`self-update` commands — see [[gateway-cli]].)

## Commands

| Command | Purpose |
|---|---|
| `create-tenant` | Creates a tenant with tier-based limits (community/developer-pro/enterprise) |
| `list-tenants` | Lists all tenants, or shows detail for one `--tenant-id` |
| `delete-tenant` | Deletes a tenant and its data (confirms unless `--force`) |
| `generate-api-key` | Issues a new API key for a tenant, with an expiry window |
| `list-api-keys` | Lists API keys for a tenant (key IDs shown truncated) |
| `revoke-api-key` | Revokes one API key (confirms unless `--force`) |
| `export-telemetry` | Exports a tenant's telemetry events as JSON or CSV (GDPR data export) |
| `delete-telemetry` | Permanently deletes a tenant's telemetry data (GDPR right to be forgotten; confirms unless `--force`) |
| `serve` | Starts the ICE gateway (`uvicorn.run("ice.main:app", ...)`) |
| `init` | Connects an `ICEKernel` and reports DB/Redis health — intended as a setup/test command |

All commands other than `serve` follow the same shape: build a Rich `Progress` spinner, do the async work inside a nested `asyncio.run(...)`-wrapped coroutine, and print a formatted `Panel`/`Table` result.

## Why nearly every command fails against the current tree

- **`create-tenant`, `list-tenants`, `delete-tenant`, `generate-api-key`, `list-api-keys`, `revoke-api-key`, `init`** each construct an `ICEKernel(...)` as their first step. As documented in [[multi-tenant-security]] and [[overview]], `ICEKernel.__init__` calls `SecurityManager(license_key)` with a positional argument that `SecurityManager.__init__` doesn't accept, and later calls `verify_or_exit()`/`register_node()`, neither of which exists on `SecurityManager`. Every one of these commands fails at kernel construction before reaching its own logic.
- Independent of the kernel-construction failure, the six tenant/API-key commands (`create-tenant` through `revoke-api-key`) each separately instantiate a *second*, unrelated `SecurityManager()` (no `license_key` argument this time — this construction succeeds) and call methods on it — `create_tenant`, `get_tenant`, `list_tenants`, `delete_tenant`, `generate_api_key`, `list_api_keys`, `revoke_api_key` — none of which are defined on `SecurityManager` (see [[multi-tenant-security]] for the full gap). Even if the `ICEKernel` construction issue were fixed, these six commands would still fail with `AttributeError` on this second call.
- **`export-telemetry` and `delete-telemetry`** don't touch `ICEKernel`/`SecurityManager` at all — they build a FastAPI `TestClient(app)` against `ice.main:app` and call `GET /v1/telemetry/export` / `DELETE /v1/telemetry/data`. Neither route exists in `ice/main.py` (only `/v1/telemetry/status` and `/v1/telemetry/force-flush` are defined — see [[gateway-api]]), so both commands print a formatted failure message reporting a 404, rather than raising.
- **`serve`** is structurally independent of all the above — it's a thin wrapper around `uvicorn.run("ice.main:app", ...)` with no kernel or SecurityManager construction, so it is not affected by these gaps (though importing `ice.main` still triggers all of that module's import-time OTel setup — see [[gateway-api]]).

## Notable design details (independent of the gaps above)

- `generate-api-key` prints the newly generated key in cleartext to the console with an explicit one-time-display warning ("Save this key securely. It will not be shown again.") — the intended UX pattern is that keys are not retrievable after creation.
- `list-api-keys` and `list-tenants` truncate IDs for table display (`key_id[:16] + "..."`, `tenant_id[:8] + "..."`) — display-only truncation, not a security measure.
- `delete-tenant`, `revoke-api-key`, and `delete-telemetry` all gate on an interactive `click.confirm(...)` prompt unless `--force` is passed, consistent with these being destructive, hard-to-reverse operations.
- `export-telemetry`'s CSV branch writes a fixed column schema (`timestamp, event_type, tenant_id, session_id, user_id, details`) with `details` serialized as a JSON string per row; the JSON branch dumps the raw response body with `default=str` for non-JSON-native types (e.g. datetimes).
