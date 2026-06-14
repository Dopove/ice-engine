# 📚 ICE V3 API Reference

This is the definitive technical reference for the ICE V3.0.0 SDK. All configurations are type-safe and validated via Pydantic.

## 1. Core Classes

### `ice.Client`
The primary interface for ICE. Recommended for production.

**Constructor:**
- `tenant_id` (str): Unique identifier for the tenant.
- `client_budget` (Optional[CognitiveBudget]): Instance-level physics settings.
- `pre_query_hooks` (Optional[List[Callable]]): Async functions to run before a query.
- `post_query_hooks` (Optional[List[Callable]]): Async functions to run after a query.
- `custom_headers` (Optional[Dict[str, str]]): Headers for outbound proxy calls.

**Methods:**
- `await .ingest(source, config)`: Voxelizes data from a URI.
- `await .query(prompt, model, config)`: Executes an LLM turn with context.

---

## 2. Configuration Models (Type-Safe)

### `ice.CognitiveBudget` / `ice.QueryConfig` / `ice.IngestConfig`
These models share the same schema. Use `QueryConfig` or `IngestConfig` for per-request overrides.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `post_limit` | int | 8192 | Max tokens for the final LLM prompt. |
| `pre_limit` | int | 5 | Max "needles" retrieved from memory. |
| `max_vram_mb` | int | 8192 | Hard VRAM cap for the native kernel. |
| `fidelity` | float | 0.5 | Ingestion resolution (0.0 to 1.0). |
| `physics_engine` | str | "native" | `native` (RCC) or `standard`. |

---

## 3. Global Functions

- `ice.set_defaults(**kwargs)`: Sets application-wide defaults for the `CognitiveBudget`.
- `await ice.ingest(...)`: Top-level convenience ingest (uses default singleton).
- `await ice.query(...)`: Top-level convenience query (uses default singleton).

---

## 4. Security & Environment

| Variable | Description |
| :--- | :--- |
| `ICE_LICENSE_JWT` | **Required.** Your hardware-bound JWT license. |
| `ICE_TELEMETRY_SINK` | Destination for crash reports (internal). |
| `ICE_AUDIT_LOG_SINK` | Destination for your operational logs (S3/File). |
