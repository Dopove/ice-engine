# ⚙️ Customizing ICE V3

ICE is designed for surgical control. You can configure your cognitive engine at four distinct levels of granularity.

## 1. Global Defaults
Set app-wide physics before initialization.

```python
import ice

ice.set_defaults(
    post_limit=16384,
    max_vram_mb=12288
)
```

## 2. The Local-Tier Client
For isolated cognitive environments (e.g., multi-tenant SaaS), instantiate a dedicated `Client`.

```python
# Creates an isolated instance for a specific tenant
acme_client = ice.Client(
    tenant_id="acme-corp",
    client_budget=ice.CognitiveBudget(post_limit=32000)
)
```

## 3. Surgical Request Overrides
For individual queries that require extreme precision or massive context windows, use `QueryConfig`.

```python
response = await acme_client.query(
    "Deep analysis of financial contracts.",
    model="claude-3.5-sonnet",
    config=ice.QueryConfig(post_limit=128000)
)
```

## Available Customization Features
The following settings can be configured via `ice.CognitiveBudget`:

| Setting | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `post_limit` | int | Total token budget for the final LLM prompt. | 8192 |
| `pre_limit` | int | Max number of memory "needles" to inject. | 5 |
| `max_vram_mb` | int | VRAM limit for native kernel operations. | 8192 |
| `fidelity` | float | Semantic resolution of ingestion (0.0-1.0). | 0.5 |
| `physics_engine` | str | Execution mode: `native` or `standard`. | "native" |

---
Next: **[Production Escape Hatches](./escape_hatches.md)**
