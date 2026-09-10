---
type: operations
title: Postgres Auto-Provisioning
description: ensure_postgres_available in ice/setup_db.py -- how ICE checks for a reachable Postgres and, if missing, lets the developer choose between a Docker container or a native OS-package install before applying the schema.
tags: [postgres, docker, provisioning, cli, database]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T16:41:07.026Z
sources:
  - id: openwiki-source-171667cf123329a8f00acf34
    resource: repo://ice/kernel.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
  - id: openwiki-source-736c96f9bde7562ed596282b
    resource: repo://ice/setup_db.py
  - id: openwiki-source-2ea80c7961972ad7227855f6
    resource: repo://tests/unit/test_db_bootstrap.py
generated: { by: "claude-code", at: "2026-09-08T16:41:07.026Z" }
---

## Why this exists

Both consumption paths that actually persist data — the gateway (`ICEServer`) and the SDK (`ICEKernel`) — require a real Postgres instance; neither falls back to DuckDB or any other embedded store (see [[architecture/overview]]). Previously, a missing Postgres just meant `degraded_mode`, `asyncpg.create_pool` failures, or an unhelpful connection-refused traceback with no guidance. `ice/setup_db.py`'s `ensure_postgres_available()` closes that gap: it checks connectivity first, and — only if genuinely unreachable — offers to provision Postgres, letting the developer pick Docker or a native install rather than the tool silently doing either.

## Method resolution: never installs unattended

`ensure_postgres_available(database_url=None, auto_provision=True, method=None)` first tries a real connection (`asyncpg.connect`, 3s timeout via `_can_connect`) and returns immediately if it succeeds — the common case on any machine that already has Postgres running costs one fast connection attempt and nothing else.

If unreachable and `auto_provision=True`, the provisioning method is resolved in this strict order (`_resolve_provision_method`):

1. The `method` argument, if the caller passed `"docker"`, `"native"`, or `"skip"` explicitly.
2. The `ICE_DB_PROVISION_METHOD` env var, same three values.
3. An **interactive prompt** (`prompt_provision_method`) — but only if `sys.stdin.isatty()` is true. It prints the choice and reads one line:
   ```
   [ICE] PostgreSQL is required and isn't reachable.
   How would you like it provisioned?
     [1] Docker container (isolated, easiest to remove later)
     [2] Native install via your OS package manager
     [3] Skip -- I'll set it up myself
   ```
4. `"skip"` — if none of the above apply (e.g. running inside CI, a daemonized server, or any other non-interactive context), the function never guesses and never installs anything; it prints manual instructions for both methods and returns `False`.

`auto_provision=False` skips straight to the manual-instructions path regardless of TTY state — this is what `ICE_AUTO_PROVISION_DB=0` maps to at the call sites (see below).

## Docker path

`_provision_via_docker(database_url)`:
- Requires `is_docker_available()` — the `docker` CLI on `PATH` *and* a live daemon (`docker info` actually succeeds, not just the binary existing).
- Reuses a single named container, `ice-postgres` (`ICE_DOCKER_PG_CONTAINER`). `_docker_container_state` inspects it first: `docker start` if it exists but is stopped; a no-op if already running; otherwise a fresh `docker run -d`.
- The image is `pgvector/pgvector:pg16` (`ICE_DOCKER_PG_IMAGE`), not plain `postgres:16` — the schema applied by `setup()` (below) does `CREATE EXTENSION IF NOT EXISTS vector`, which a vanilla Postgres image doesn't ship.
- Container env vars (`POSTGRES_USER`/`_PASSWORD`/`_DB`) match `ICE_DB_USER`/`ICE_DB_PASSWORD`/`ICE_DB_NAME` (`ice_user`/`ice_password`/`ice_db` by default) — the official Postgres image creates that role/database itself on first boot, so the Docker path does **not** call the role/db-creation SQL the native path does.
- The container port maps to whatever port `DATABASE_URL` specifies (parsed via `urllib.parse.urlparse`, default 5432), and data persists in a named volume (`ice_postgres_data`) so a `docker rm`/re-`run` doesn't lose data as long as the volume survives.

## Native path

`_provision_via_native()` reuses the OS-package-manager detection/install machinery: `detect_package_manager()` picks the first of `apt-get`/`dnf`/`yum`/`pacman`/`zypper` (Linux) or `brew` (macOS) found on `PATH`; if Postgres isn't already installed (`is_postgres_installed()`, checked via `psql`/`postgres` binaries), it runs that manager's install command, then its service-start commands (`systemctl enable --now postgresql`, or platform equivalents — `postgresql-setup --initdb` first on Fedora/RHEL, `initdb` first on Arch). If Postgres is already installed but just unreachable, it skips straight to the start commands (most likely the service simply isn't running).

Either way, it finishes with `_create_role_and_db()` — best-effort `CREATE ROLE`/`CREATE DATABASE` via `sudo -u postgres psql` (falling back to `psql -U postgres` if that fails), idempotent via a `pg_roles` existence check. Unlike the Docker path, a native install does **not** automatically get the `pgvector` extension — `_print_manual_instructions` calls this out explicitly (e.g. Debian/Ubuntu ship it as a separate `postgresql-16-pgvector` package) rather than silently letting the later `CREATE EXTENSION vector` fail with no context.

## After provisioning: polling and schema application

Once either path reports success, `_wait_for_connect` polls `_can_connect` up to 15 times at 2s intervals (30s total) before giving up — a freshly-started Docker container in particular needs a moment before it accepts connections. If still unreachable after that, or if provisioning itself failed, `_print_manual_instructions` is printed (both Docker and native commands, plus the `ICE_SKIP_INFRA_CONNECT=1` degraded-mode escape hatch) and the function returns `False`.

`ensure_postgres_available()` only gets the server *reachable* — applying/updating the schema (tables, the `vector` extension, indexes, the default dev tenant) is a separate step, `setup_db.setup()`, unchanged from before this work. `ice db update` (see [[gateway-cli]]) chains both: ensure reachable, then apply schema, in one command.

## Where it's called from

Both wired in as the very first thing each container attempts before opening its `asyncpg` pool, both reading `ICE_AUTO_PROVISION_DB` (default `"1"`) for the `auto_provision` flag:

- **`ICEServer.startup()`** (`ice/main.py`, see [[architecture/gateway-api]]) — a failure here (including the `RuntimeError` `ensure_postgres_available` raises when it returns `False`) is caught by the surrounding `except Exception` and folds into `degraded_mode = True`, same as any other infra failure; the gateway still boots.
- **`ICEKernel.connect()`** (`ice/kernel.py`, see [[architecture/overview]]) — no surrounding catch, so that same `RuntimeError` propagates straight out of `connect()`.

## Testing

`tests/unit/test_db_bootstrap.py` covers the pure/mockable surface — package-manager detection across simulated `Darwin`/`Linux`/unsupported platforms, `is_postgres_installed`, every `_PG_PACKAGE_MANAGERS` entry having both an install and start command, `_resolve_provision_method`'s full precedence chain (explicit → env var → interactive-prompt-when-tty → skip-when-not), and `_docker_container_state` parsing `docker inspect` output for both a running container and a nonexistent one. None of these tests invoke a real `subprocess` install/run command or a real database connection — `platform.system`, `shutil.which`, and `subprocess.run` are mocked throughout.
