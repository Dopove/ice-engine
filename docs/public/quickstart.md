# 🚀 ICE V3 Quickstart

This guide will show you how to mount the ICE memory engine into your application in under 60 seconds.

## 1. Installation
ICE is a standard Python library. Install the compiled artifact using `pip`.

```bash
pip install ice-engine-3.0.0.whl
```

## 2. Basic Usage (The "1-Minute" Path)
For simple scripts or non-production prototypes.

```python
import ice
import asyncio
import os

# 💡 PRO-TIP: Ensure your license is in the environment
os.environ["ICE_LICENSE_JWT"] = "your_signed_jwt_here"

async def main():
    await ice.ingest("s3://data-lake/architecture.pdf")
    response = await ice.query(prompt="Analyze this.", model="gpt-4o")
    print(response)

asyncio.run(main())
```

## 3. Production Usage (The "Sovereign" Path)
For multi-tenant SaaS applications requiring isolation and type-safety.

```python
import ice
import asyncio

# 1. Set global node defaults
ice.set_defaults(max_vram_mb=16384, post_limit=16000)

async def handle_request(tenant_id, user_prompt):
    # 2. Instantiate a state-isolated client
    client = ice.Client(
        tenant_id=tenant_id,
        client_budget=ice.CognitiveBudget(fidelity=0.9)
    )

    # 3. Type-safe query with request-level override
    return await client.query(
        prompt=user_prompt,
        model="claude-3.5-sonnet",
        config=ice.QueryConfig(post_limit=32000)
    )
```

## 4. Troubleshooting
If the application exits with 🛑 `[ICE SECURITY FAULT]`, it means your `ICE_LICENSE_JWT` is missing, expired, or not bound to this specific hardware. 

See **[Operations & Troubleshooting](./operations.md)** for details.

---
Next: **[API Reference](./api_reference.md)**
