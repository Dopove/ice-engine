# 🧊 Indexless Context Engine (ICE)

**ICE** is an open-source, ultra-low-latency persistent memory engine for LLM agents.

Instead of building complex vector databases and managing chunking logic, ICE acts as an invisible **SDK Middleware**. You wrap your standard OpenAI (or Anthropic) client, and ICE automatically injects limitless episodic memory into your agent's context window.

## 🚀 Why ICE?

*   **Zero-Config Local Mode:** Boots instantly with a local DuckDB file. No Docker, no Postgres required to get started.
*   **Zero Code Changes:** Wrap your existing OpenAI SDK client. No new API endpoints to learn.
*   **Production Hardened:** Built for multi-tenant isolation, automatic rate limiting, and structured circuit-breaking.
*   **Multimodal Ready:** (Optional) Lazy-load integration with RAG-Anything to ingest complex PDFs, images, and tables.

## 📦 Installation

ICE is available via pip. 

```bash
# Core installation (Zero-Conf DuckDB local memory)
pip install ice-engine

# With multimodal ingestion (PDFs, Images, OCR)
pip install ice-engine[multimodal]
```

## ⚡ Quickstart: The 3-Line Drop-in

ICE wraps your existing LLM client. It intercepts `chat.completions.create`, automatically retrieves relevant past conversations, injects them into the system prompt, and saves the new response.

```python
import asyncio
import os
from openai import AsyncOpenAI
from ice.wrapper import ICEWrapper

async def main():
    # 1. Initialize your standard client
    base_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # 2. Wrap it with ICE (Local DuckDB mode enabled by default)
    # This automatically persists to ~/.ice/ice_memory.db
    client = ICEWrapper(base_client)

    # 3. Use your client exactly as you normally would!
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello! Please remember that my favorite framework is ICE."}
        ]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
```

*The next time you run this script and ask "What is my favorite framework?", the ICE wrapper will automatically inject the memory before sending the prompt to OpenAI.*

## 🏗️ Architecture

ICE uses an interceptor pattern combined with a layered storage backend:
1.  **Wrapper Layer:** `ICEWrapper` proxies the OpenAI SDK.
2.  **Episodic Manager:** Summarizes and embeds the conversation.
3.  **Storage Layer:** Pluggable backend (DuckDB by default, PostgreSQL for cluster deployments).

For deep technical specifications on the engine's internals, see [docs/architecture/ENGINE_INTERNALS.md](docs/architecture/ENGINE_INTERNALS.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
