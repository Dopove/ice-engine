# 🛠️ Enterprise Escape Hatches

ICE is built to fit into the world's most complex production environments. We provide "Escape Hatches" that allow you to customize the engine's behavior without modifying the core binary.

## 1. Middleware Hooks
Inject your own logic before or after a query. This is ideal for PII scrubbing, toxicity filtering, or custom audit logging.

```python
async def pii_scrubber(prompt: str) -> str:
    # Redact sensitive data before it hits the LLM
    return prompt.replace("SSN:XXX-XX-XXXX", "[REDACTED]")

client = ice.Client(
    tenant_id="healthcare-corp",
    pre_query_hooks=[pii_scrubber]
)
```

## 2. Custom Transport & Proxies
Many enterprises route LLM traffic through internal gateways. You can pass custom headers or base URLs to the ICE Client.

```python
client = ice.Client(
    tenant_id="fintech-global",
    custom_headers={"X-Corporate-Proxy-Auth": "secret-token"}
)
```

## 3. Data Portability
Never get locked in. Use `export_tenant_data` to move your Voxel history to your own long-term storage (e.g., S3 Glacier).

```python
# Coming soon: API for full VMM state migration
# await client.export_tenant_data(destination="s3://my-audit-bucket/voxels/")
```

---
Return to **[Main Index](./index.md)**
