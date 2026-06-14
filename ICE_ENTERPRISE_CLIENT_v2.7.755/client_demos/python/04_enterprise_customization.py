import asyncio
import os
from ice.sdk import init, get_client
from ui import UI

async def run_customization_demo():
    UI.header("ICE: Enterprise Customization & Compliance Demo")
    
    # --- Define all Enterprise Tunables ---
    custom_tunables = {
        "memory_cap_gb": 64.0,
        "max_stitch_concurrency": 50,
        "retention_days": 365,
        "chunk_size": 12000,
        "max_input_tokens": 128000,
        "chunk_overlap": 1000,
        "max_continuations": 100,
        "priority_memory_limit": 5,
        "reasoning_recall_limit": 10,
        "privacy_masking": "strict",
        "llm_routing_strategy": "sovereign-local",
        "dynamic_output_budget": False, # Explicitly disable for this demo
        "default_output_tokens": 512, # Custom default output
    }

    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    UI.system("Booting live ICE Kernel with custom tunables...")
    
    # Initialize the client with all custom tunables
    ice_client = await init(
        license_key=os.getenv("ICE_LICENSE_JWT") or "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ",
        **custom_tunables
    )
        
    UI.system("ICE Client initialized with Staff-Engineer compliance overrides.")
    UI.system("The following runtime boundaries have been programmatically applied to the kernel:")
    
    current_config = ice_client.config
    
    UI.param("Memory Guardian Cap", f"{current_config.get('memory_cap_gb')} GB")
    UI.param("Max Stitch Concurrency", current_config.get('max_stitch_concurrency'))
    UI.param("Ledger Retention", f"{current_config.get('retention_days')} Days")
    UI.param("Chunking Physics", f"{current_config.get('chunk_size')} chars/segment")
    UI.param("Chunk Overlap", f"{current_config.get('chunk_overlap')} chars")
    UI.param("Max Input Tokens", current_config.get('max_input_tokens'))
    UI.param("Max Continuations", f"{current_config.get('max_continuations')} turns")
    UI.param("Priority Memory Limit", f"{current_config.get('priority_memory_limit')} items")
    UI.param("Reasoning Recall Limit", f"{current_config.get('reasoning_recall_limit')} items")
    UI.param("Privacy Masking", current_config.get('privacy_masking'))
    UI.param("Routing Strategy", current_config.get('llm_routing_strategy'))
    UI.param("Dynamic Output Budget", current_config.get('dynamic_output_budget'))
    UI.param("Default Output Tokens", current_config.get('default_output_tokens'))

    UI.system("The underlying PostgreSQL Ledger and ContextPager will now strictly adhere to these policies.")

if __name__ == "__main__":
    asyncio.run(run_customization_demo())
