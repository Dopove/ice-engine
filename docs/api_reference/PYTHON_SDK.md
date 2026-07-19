# 📦 ICE Python SDK: Master Configuration Pattern (v3.1.75)

> **🔐 IP PROTECTION NOTICE**: The Python SDK is distributed as a pre-compiled wheel (`.whl`). The package contains a machine-code binary (`.so`) created by Nuitka, which seals all proprietary algorithms and mathematical models. Separate wheels are provided for each SKU, Python version (3.10, 3.11, 3.12), and CPU architecture (`x86_64`, `aarch64`). **Source code is not provided.**

The ICE Python SDK allows developers to integrate the **Indexless Context Engine** natively into their applications using an architecture-first approach. 

## 1. The Singleton Pattern (Best Practice)

Production engineering teams should centralize their ICE configuration in a single file. This ensures consistent memory physics and compliance policies across the entire application.

### `core/ice_config.py`
Create this file to define your global memory operating system.

```python
import os
import asyncio
from ice.sdk import init, get_client, InfiniteContextClient

_global_ice_client: InfiniteContextClient = None

async def initialize_ice_kernel():
    global _global_ice_client
    _global_ice_client = await init(
        # Context Limits & Orchestration
        max_input_tokens=128000,
        chunk_size=8000,
        default_output_tokens=4096,
        enable_smart_sizing=True,
        
        # Storage, Compliance & Retention
        retention_days=int(os.getenv("ICE_RETENTION", "30")),                     
        upload_dir="/mnt/efs/ice_vault",       # Centralized memory storage
        rag_enable_compliance=True,            # Financial Security PII Masking
        
        # Multimodal Pipeline Settings
        rag_parser="docling",                  # High-fidelity parser
        enable_images=True,                    # Persistent Vision Engine
        enable_tables=True,
        
        # Infrastructure
        database_url=os.getenv("DATABASE_URL"),
        redis_url=os.getenv("REDIS_URL"),
        
        # Licensing (optional, can be passed via env var ICE_API_KEY)
        license_key=os.getenv("ICE_API_KEY")
    )

def get_ice_client() -> InfiniteContextClient:
    if _global_ice_client is None:
        raise RuntimeError("ICE Kernel not initialized. Ensure initialize_ice_kernel() is called at startup.")
    return _global_ice_client

# Example of how to call initialize_ice_kernel if not using FastAPI lifespan events
# if __name__ == "__main__":
#     asyncio.run(initialize_ice_kernel())
```
This pattern ensures the ICE Kernel is initialized once globally and can be retrieved consistently across your application.

## 2. Using the Client in Agentic Logic

Developers building features just import the pre-configured `ice_client`. They don't need to know anything about vector databases or chunking.

### `services/agent.py`
```python
from core.ice_config import get_ice_client

async def run_autonomous_coding_swarm(user_id, session_id, user_query):
    ice_client = get_ice_client()
    
    # 1. Infinite Context Generation
    # Recall, Stitching, and Syntax Protection are handled automatically!
    response_stream = await ice_client.chat.completions.create(
        model="claude-3-5-sonnet", 
        messages=[{"role": "user", "content": user_query}],
        x_session_id=session_id,
        x_user_id=user_id,
        
        # Flawless Agentic Features
        tools=[...], 
        tool_choice="auto",
        stream=True
    )
    
    async for chunk in response_stream:
        # ICE protects the JSON tool-calls during stitching!
        print(chunk)
```

## 3. Multimodal Ingestion (One-Line)

Ingest complex documents or images directly into the 100B token horizon.

```python
from core.ice_config import get_ice_client

async def ingest_document(file_path: str, user_id: str, session_id: str):
    ice_client = get_ice_client()
    # ICE handles partitioning and indexing based on the master config
    await ice_client.ingest(
        file_path=file_path,
        x_user_id=user_id,
        x_session_id=session_id
    )
```

## 4. Key Advantages for Productions
1.  **Architecture Consistency**: The Lead Architect controls retention and PII policies globally.
2.  **Clean Code**: Feature developers focus purely on prompts and business logic.
3.  **Future-Proofing**: Switch parsers or storage backends in `ice_config.py` without touching a single line of agentic code.
4.  **Hardware-Lock Efficiency**: All initialization handshakes and license checks are abstracted away.

---
**ICE Engine Contributors**  | [github.com/ice-engine](https://www.github.com/ice-engine/) | community@ice-engine.org  
**(c) 2026 ICE Engine Contributors**
