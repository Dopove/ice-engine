# 🧠 ICE Engine Internals

This document details the architecture and technical decisions underlying the Indexless Context Engine (ICE) open-source release.

## 1. The Middleware Architecture

ICE is designed as an **SDK Middleware**. Instead of forcing users to adopt a proprietary API or proxy through a separate server, ICE wraps the existing `OpenAI` or `Anthropic` Python clients.

### Request Interception
When `client.chat.completions.create` is called:
1. The `ICEWrapper` intercepts the request.
2. It extracts the most recent user messages.
3. It performs a vector similarity search against the **Episodic Memory Store**.
4. The retrieved context is formatted and injected into the developer's original system prompt.
5. The request is forwarded to the underlying LLM provider.
6. The response is saved back to the memory store asynchronously.

## 2. Storage Layer: Local-First DuckDB

By default, ICE operates in a "Zero-Conf" mode using DuckDB.

*   **Why DuckDB?** DuckDB provides the analytical power and structured querying capabilities of PostgreSQL without requiring a daemon process. It writes to a local `.db` file (defaulting to `~/.ice/ice_memory.db`).
*   **Production Scaling:** The `MemoryStore` interface is pluggable. While DuckDB is the default for ease of use, production deployments can inject a PostgreSQL or Redis cluster connection string into the `ICEWrapper`.

## 3. Multimodal Lazy Loading

To keep the core engine lightweight (under 10MB), multimodal capabilities (PDF OCR, Image parsing) are isolated in the `ice-engine[multimodal]` extra.

We utilize a custom `OptionalModule` pattern. The `raganything` dependency is only imported at runtime when `IngestionPipeline.ingest_document()` is explicitly invoked. If the extra is missing, the engine gracefully raises an `ImportError` directing the developer to install the multimodal package.

## 4. C-Extension Core (RCC FFI)

Certain performance-critical operations (like precise token counting and routing heuristics) are written in C and compiled as native extensions (`ice_core.so` / `ice_core.dylib`). The Python wrapper uses standard `ctypes` to interface with these binaries.
