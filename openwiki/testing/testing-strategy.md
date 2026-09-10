---
type: operations
title: Testing Strategy
description: The pytest suite's shared fixtures and Docker-availability gating, the CI pipeline stages, and why the integration test built to exercise a real OTLP collector export never actually runs in CI as currently wired.
tags: [testing, pytest, ci, docker, otel, coverage]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-164e2da859b5277df81c7d94
    resource: repo://.github/workflows/ci.yml
  - id: openwiki-source-f011a030ad13c406633402c0
    resource: repo://docker-compose.test.yml
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-f0a6e7dc03522b2682f88655
    resource: repo://tests/conftest.py
  - id: openwiki-source-f63e319948ff3548bc8d31bd
    resource: repo://tests/integration/test_otel_export.py
  - id: openwiki-source-828c5ef19f0bba6540b81f0f
    resource: repo://tests/unit/test_concurrency_torture.py
  - id: openwiki-source-82c13c65c055069ae4c1f8a4
    resource: repo://tests/unit/test_production_hardening.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Layout

`tests/unit/` covers isolated component behavior (concurrency, PII scrubbing, federated search, production hardening); `tests/integration/` covers cross-component flows against a running stack (telemetry, OTel export, context rot). Both share fixtures from `tests/conftest.py`.

## Shared fixtures (`tests/conftest.py`)

- **`setup_environment`** (session-scoped, autouse) — forces `ICE_DEVICE=cpu`, `MINERU_DEVICE=cpu`, `ICE_BYPASS_LICENSING=1`, `ICE_SKU=ICE-UNLIMITED` for every test run, and best-effort patches `ice.build_config.ICE_SKU` if that module exists.
- **`mock_db_pool`** (session-scoped) — a fully mocked `asyncpg`-shaped pool (`AsyncMock`) whose `acquire()` yields a mock connection defaulting `execute()` to `"DELETE 1"` and `fetch()` to `[]`.
- **`patch_ice_server_dependencies`** (session-scoped, autouse) — if `ice.main` imported successfully and exposes a module-level `ice_server`, patches its `db_pool` attribute to `mock_db_pool` for the whole session (and `rag` too, if present) so tests never touch a real database. This assumes `ice.main` itself imports cleanly (which it does independently of the various `ICEKernel`/`SecurityManager`/`ice/cli.py` import issues documented in [[overview]] and [[admin-cli]] — those live in different modules).
- **`pytest_collection_modifyitems`** — a collection hook that decides, once per session, whether "Docker" is available by probing `localhost:5432` (Postgres) and `localhost:6379` (Redis) with a 0.5s socket timeout (`is_docker_available`). If neither port is open, it walks every collected test and adds a `skip` marker to any test whose path satisfies: `("integration" in path and "test_telemetry" not in path) or "test_community_limits.py" in path or "test_federated_search.py" in path` — **unless** that specific test is marked `no_docker`. Due to Python operator precedence, this means: any file under `tests/integration/` whose filename doesn't contain `test_telemetry` is skipped wholesale when Postgres/Redis aren't reachable, while files with `test_telemetry` in their name (`test_telemetry_integration.py`) are exempted (the code comment states they "use mocks").

## The Docker-gate / CI docker-compose mismatch

This interacts badly with the CI integration-tests job's actual Docker stack. `docker-compose.test.yml` starts only two services — `ice` (the gateway) and `otel-collector` — **no Postgres, no Redis**. `is_docker_available()` checks exactly those two ports (5432, 6379) and nothing else (not 4317, the collector's own port). The practical result:

- **Every test file under `tests/integration/` other than `test_telemetry_integration.py`** — including `test_otel_export.py`, `test_context_rot.py` — gets the `skip` marker applied in CI, because the compose stack never opens 5432 or 6379.
- Within `test_otel_export.py`, only the one test explicitly decorated `@pytest.mark.no_docker` (`test_no_dead_telemetry_endpoint`, a pure filesystem/string check with no infra dependency) escapes this and actually runs in CI.
- In particular, `test_trace_export_to_collector` — the test built to probe a live collector connection and perform a real OTLP span export — has no `no_docker` marker, so it is skipped by the collection hook in CI regardless of whether `otel-collector` is actually running and reachable. The CI job's own "wait for services" step (`curl -f http://localhost:8000/live`) only confirms the `ice` container is up; nothing in the pipeline confirms the collector is exercised by a test, because the test that would do so never executes.

`no_docker` is not registered as a custom marker anywhere in `pyproject.toml`'s pytest configuration, so pytest emits `PytestUnknownMarkWarning` for every use of it — non-fatal (no `filterwarnings = error` config found), but it means a typo in the marker name would silently produce the same "always skipped" behavior with no error to signal it.

## CI pipeline (`.github/workflows/ci.yml`)

Sequential jobs, each gating the next via `needs`:

1. **`lint-and-security`** — Ruff, Black `--check`, mypy, Bandit (`|| true` — never fails the job), Safety (`|| true` — same), reports uploaded as artifacts regardless of findings.
2. **`unit-tests`** — runs `pytest tests/unit/` with `--cov-fail-under=80`; this *does* fail the job if coverage drops below 80%, unlike the security scanners above.
3. **`integration-tests`** — gated to PRs and pushes to `main` only (`if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main'`); brings up `docker-compose.test.yml`, waits, runs `pytest tests/integration/` — subject to the Docker-gate mismatch above — then tears the stack down (`if: always()`).
4. **`build-and-push`** — only on push to `main`; builds and pushes the Docker image to `ghcr.io`.
5. **`deploy-staging`** (push to `main`) / **`deploy-production`** (manual `workflow_dispatch` with `environment: production`) — both run `terraform init`/`workspace select`/`apply` directly from the CI runner using long-lived AWS credentials from repository secrets; production additionally runs `terraform plan` before `apply` and a post-deploy smoke check against `/v1/health` and `/v1/telemetry/status`.
6. **`notify`** — Slack notification, `if: always()`, regardless of upstream job outcomes.

## Inert "torture" tests

`tests/unit/test_concurrency_torture.py` (`test_concurrency`, a 110-request burst test asserting exactly 100×200 + 10×429 against a running gateway) and `tests/unit/test_production_hardening.py` (`test_metrics`, `test_rate_limiting`) are each explicitly decorated `@pytest.mark.skip(reason="Networking dependent test")`. They're written to run as standalone scripts (each has its own `if __name__ == "__main__": asyncio.run(main())`) against a gateway expected to already be running on `localhost:8081` — a port nothing in `docker-compose.test.yml` or the CI workflow starts a service on (the compose file's `ice` service publishes `8000`, not `8081`). As committed, these are permanently inert under `pytest` and were not designed to run via the CI job's compose stack at all.
