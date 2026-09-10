---
type: operations
title: "Gateway CLI: serve, mount, db, self-update"
description: ice/cli.py, the registered `ice` console script -- its formerly-broken license_cli import (now removed), and its serve/mount/help/db-update/self-update commands.
tags: [cli, console-script, click, gateway]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
sources:
  - id: openwiki-source-c6ad3edea88b91e6531f91d7
    resource: repo://ice/cli.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-9fe3a610596da7b7f2c71115
    resource: repo://setup.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
---

## The registered `ice` command

`ice/cli.py`'s `main` click group is what `pyproject.toml`'s `[project.scripts]` (`ice = "ice.cli:main"`) and `setup.py`'s `entry_points` both register as the `ice` console script — distinct from `ice/admin/cli.py`'s tenant-management command group, which is not registered as a console script at all (see [[admin-cli]]).

**It previously couldn't be imported at all.** The module imported `from .license_cli import license` — a module (`ice/license_cli.py`) that never existed anywhere in this tree — so importing `ice.cli`, and therefore running `ice` in any form, raised `ModuleNotFoundError` immediately. That import (and the `main.add_command(license)` wiring it fed) has been removed; nothing in the codebase ever defined what a `license` command group should do, so there was no real functionality to restore — this was a dead reference, not a disabled feature.

## Commands

| Command | Purpose |
|---|---|
| `help` | Prints the group's help text (same content `ice --help` or bare `ice` shows) |
| `serve` | `uvicorn.run("ice.main:app", ...)` — launches the gateway |
| `mount` | One-shot document ingestion via the SDK |
| `db update` | Ensures Postgres is reachable (auto-provisioning if needed), then applies the schema |
| `self-update` | `pip install --upgrade ice-engine` |

### `help`

A thin, explicit alias: `ctx.parent.get_help()` returns the same usage/command listing Click's built-in `--help` (or a bare `ice` invocation, since Click groups default to `no_args_is_help=True`) already produces. Added on top of Click's automatic help so `ice help` works too, matching the convention of tools like `git help`/`docker help`.

### `serve`

Unchanged from before — a thin wrapper: prints a banner, then hands off entirely to `uvicorn.run("ice.main:app", host=host, port=port, reload=reload)`. `--port` defaults from `ICE_PORT` (env), `--host` defaults `0.0.0.0`, `--reload` is a flag for dev auto-reload. Once this actually runs (which it now can, since the module imports), it triggers everything documented in [[architecture/gateway-api]] — including the new Postgres auto-provisioning step in `ICEServer.startup()` (see [[database-provisioning]]).

### `mount`

Unchanged, and still broken independent of the `license_cli` fix: it calls `ice.sdk.init()` (which fails constructing `ICEKernel` — see [[architecture/overview]]) and, even past that, `ice_client.ingest(file_path=path, session_id=session_id, x_user_id=user_id)`, which calls `IngestionPipeline.ingest_path` — a method that doesn't exist (see [[workflows/ingestion-and-rag]]). Fixing the console-script import makes this command *reachable*; it doesn't make it *work*.

### `db update` (new)

Chains the two pieces built for Postgres provisioning: `setup_db.ensure_postgres_available(auto_provision=...)` (default `True`, toggled via `--auto-provision`/`--no-auto-provision`), then — only if that succeeds — `setup_db.setup()` to create/migrate the schema (tables, `vector` extension, indexes, default dev tenant; see [[database-provisioning]]). If provisioning fails, it exits non-zero with an error rather than attempting the schema step against an unreachable database.

### `self-update` (new)

A direct `subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "ice-engine"])`, using the *running* interpreter's `pip` rather than a bare `pip` on `PATH` (so it upgrades the same environment `ice` is actually running from). `--pre` adds `--pre` to include pre-release versions. Exits with pip's own return code — no output parsing or version comparison, it's a direct pass-through.
