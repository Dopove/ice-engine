# 📦 ICE Native Integration: Using ICE as a Library (v2.7.756)

For enterprises that already maintain their own API servers, ICE can be integrated as a **Native Python Library**. This eliminates the extra network hop of a engine and allows you to bake "Infinite Context" directly into your existing product logic.

## 1. Core Architecture: The Library Mode
Instead of calling `http://localhost:8008`, your application imports the ICE Kernel components directly.

### Required Imports
```python
from ice.core.episodic import EpisodicManager
from ice.core.reasoning import ReasoningManager
from ice.core.pager import ContextPager, EmbeddingModel
from ice.main import generate_ice_chunks # The core stitching logic
```

## 2. Initialization Pattern
You can share your existing database and Redis pools with the ICE managers.

```python
import asyncpg
import redis.asyncio as redis

# 1. Reuse your existing infrastructure pools
db_pool = await asyncpg.create_pool(dsn=YOUR_DATABASE_URL)
redis_client = redis.from_url(YOUR_REDIS_URL)

# 2. Initialize the ICE Memory Core
embedder = EmbeddingModel() # Local ONNX-based embedding
episodic = EpisodicManager(db_pool, redis_client)
reasoning = ReasoningManager(db_pool, redis_client)
pager = ContextPager(embedder, max_tokens=128000)
```

## 3. The "Internal Context Pipeline" Pattern
Wrap your existing chat logic with the ICE `generate_ice_chunks` engine to add infinite memory to your routes.

### Example: FastAPI Native Integration
```python
from fastapi import FastAPI, Header
from ice.main import generate_ice_chunks

app = FastAPI()

@app.post("/my-api/chat")
async def secure_chat(payload: dict, x_session_id: str = Header(...)):
    # 1. Perform your internal business logic / auth
    user_id = "user_from_your_db"
    tenant_id = "tenant_id_from_your_license"
    
    # 2. Delegate the "Infinite Memory" task to the ICE Kernel
    async def response_stream():
        async for chunk in generate_ice_chunks(
            model=payload["model"],
            messages=payload["messages"],
            temperature=payload.get("temperature", 0.7),
            max_tokens=payload.get("max_tokens", 4096),
            tenant_id=tenant_id,
            session_id=x_session_id,
            user_id=user_id,
            client_api_key=YOUR_UPSTREAM_KEY
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
            
    return StreamingResponse(response_stream())
```

## 4. Why Use Library Mode?
1.  **Zero Latency**: No REST/WebSocket overhead between your app and ICE.
2.  **Shared State**: Use your application's existing authentication and session management.
3.  **Direct DB Access**: You can perform complex SQL joins across your business data and the ICE `episodic_ledger` in a single transaction.
4.  **Hardware Efficiency**: One single process manages both your API and the Memory Virtualization.

---
**DOPOVE PRIVATE LIMITED** | [dopove.com](https://www.dopove.com/)  
**(c) 2026 DOPOVE PRIVATE LIMITED**
