# 🧠 Theoretical Architecture & Integration Patterns

Integrating the Indexless Context Engine (ICE) into an Production codebase requires a paradigm shift. ICE is not merely an HTTP client library; it is a **Virtual Memory Management Unit (MMU)**. 

To maximize its capabilities (Row-Level Security, KV-Cache alignment, and Anti-Context Rot), your integration architecture must treat ICE as a core infrastructure substrate.

This document outlines the theoretical best practices and concrete architectural patterns for integrating ICE into production Python and Node.js codebases.

---

## 1. The "Singleton Kernel" Paradigm

### The Theory
In standard LLM integration, developers often instantiate a new `OpenAI()` or `Anthropic()` client inside every API route or function. 

**With ICE, this is an anti-pattern.** ICE manages connection pools to PostgreSQL (the Semantic Ledger) and Redis (the Hot Cache), and maintains internal state for the `ContextPager`. Instantiating ICE per-request will devastate your latency by constantly tearing down and rebuilding these database connection pools.

### The Solution: Initialize Once at Boot
You must use the **Singleton Pattern**. The ICE Kernel should be initialized exactly *once* during the application's startup lifecycle (e.g., in a FastAPI `startup` event or before your Express server listens for traffic). 

This single instance becomes the global "Memory Kernel" that all downstream services utilize.

---

## 2. Python Architecture: The Service Wrapper

For Python applications (FastAPI, Django, or custom CLI agents), the best practice is to abstract ICE configuration into a dedicated module and inject it via Dependency Injection.

### Step A: The Configuration Module (`core/ice_kernel.py`)
Create a central file that reads your Production customization variables from the environment and boots the kernel.

```python
import os
from ice.sdk import init, InfiniteContextClient

# Define a global placeholder for the singleton
_global_ice_client: InfiniteContextClient = None

async def boot_ice_kernel() -> InfiniteContextClient:
    """
    Called strictly once during application startup.
    Applies infrastructure physics and establishes DB pools.
    """
    global _global_ice_client
    if _global_ice_client is not None:
        return _global_ice_client

    print("[SYSTEM] Booting ICE Virtual Memory Manager...")
    
    # 1. Inject Customization Physics (Read from .env or Kubernetes ConfigMap)
    max_tokens = int(os.getenv("ICE_POST_COMPRESSION_LIMIT", 32768))
    memory_cap = float(os.getenv("ICE_MEMORY_CAP_GB", 30.0))
    license_key = os.getenv("ICE_API_KEY")
    
    # 2. Initialize the Kernel
    _global_ice_client = await init(
        license_key=license_key,
        max_input_tokens=max_tokens,
        enable_smart_sizing=True,
        rag_parser="docling" # High-fidelity ingestion
    )
    
    return _global_ice_client

def get_ice_kernel() -> InfiniteContextClient:
    """Dependency Injection provider for API routes."""
    if _global_ice_client is None:
        raise RuntimeError("ICE Kernel not booted! Ensure boot_ice_kernel() ran at startup.")
    return _global_ice_client
```

### Step B: FastAPI Injection (`main.py` & `routes.py`)

```python
# main.py
from fastapi import FastAPI
from core.ice_kernel import boot_ice_kernel

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Boot the kernel before accepting traffic
    await boot_ice_kernel()

# routes/chat.py
from fastapi import APIRouter, Depends, Header
from core.ice_kernel import get_ice_kernel

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(
    message: str,
    x_user_id: str = Header(...),
    x_session_id: str = Header(...),
    # Inject the singleton kernel here
    ice: InfiniteContextClient = Depends(get_ice_kernel) 
):
    # The route logic remains incredibly clean. ICE handles the memory physics.
    response = await ice.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}],
        x_user_id=x_user_id,
        x_session_id=x_session_id
    )
    return {"reply": response.choices[0].message.content}
```

---

## 3. Node.js Architecture: The Thin Client Class

For Node.js (TypeScript/Express), you are interacting with the `@ICE Core Team/ice-engine` Thin Client. While the heavy lifting (DB pooling) happens on the Python Engine, you still want to abstract the client instantiation to inject global routing headers (like Local-Tier Mode overrides or PII Masking).

### Step A: The Class Wrapper (`src/services/IceService.ts`)

```typescript
import { IceClient, SessionManager } from '@ICE Core Team/ice-engine';

class IceService {
    private static instance: IceClient;

    /**
     * Retrieves the Singleton Thin Client instance.
     */
    public static getInstance(): IceClient {
        if (!IceService.instance) {
            console.log("[SYSTEM] Initializing ICE Thin Client...");
            
            IceService.instance = new IceClient({
                licenseJwt: process.env.ICE_API_KEY,
                // Global overrides enforced across all Node requests
                defaultHeaders: {
                    "X-Ice-Routing-Strategy": process.env.ROUTING_PREFERENCE || "default"
                }
            });
        }
        return IceService.instance;
    }
}

export default IceService;
```

### Step B: Express Route Integration (`src/controllers/chatController.ts`)

```typescript
import { Request, Response } from 'express';
import { SessionManager } from '@ICE Core Team/ice-engine';
import IceService from '../services/IceService';

export const handleChat = async (req: Request, res: Response) => {
    // 1. Extract IDs dynamically from headers
    const session = new SessionManager(req).getContext();
    
    // 2. Retrieve the globally configured Singleton
    const ice = IceService.getInstance();

    try {
        const response = await ice.chat.completions.create({
            model: "claude-3-5-sonnet",
            messages: [{ role: "user", content: req.body.message }],
            sessionId: session.sessionId,
            userId: session.userId,
            // You can override maxTokens per-request if needed
            maxTokens: parseInt(process.env.DEFAULT_OUTPUT_TOKENS || "4096")
        });

        res.json({ reply: response.choices[0].message.content });
    } catch (error: any) {
        console.error("ICE Inference Error:", error);
        res.status(500).json({ error: "Memory Kernel Error" });
    }
};
```

---

## 4. Summary of Architectural Mandates

1.  **Never Instantiate Per-Request:** Always use the Singleton pattern (`await init()` in Python or `new IceClient()` in Node.js) during application boot.
2.  **Environment Variables Dictate Physics:** Store configuration parameters (`ICE_POST_COMPRESSION_LIMIT`, `ICE_MEMORY_CAP_GB`) in `.env` files or Kubernetes ConfigMaps. Inject these variables into the Singleton at startup. See `docs/installation/CONFIGURATION.md` for the full dictionary.
3.  **Route Dynamically via Headers:** Use `x_session_id` and `x_user_id` to enforce Row-Level Security (RLS) isolation. Do not attempt to manage conversation history arrays manually; pass the IDs and let the `ContextPager` assemble the prompt mathematically.