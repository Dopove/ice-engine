# Files

- [Episodic Memory & Reasoning Traces](episodic-memory.md) - How ICE persists and retrieves conversational history (EpisodicManager) and chain-of-thought reasoning traces (ReasoningManager), and how it strips reasoning tags from streamed LLM output.
- [FastAPI Gateway & Request Lifecycle](gateway-api.md) - How ice/main.py's FastAPI app boots, authenticates and rate-limits requests, and dispatches OpenAI/Anthropic/Gemini-compatible chat requests through generate_ice_chunks.
- [Multi-Tenant Security & Governance](multi-tenant-security.md) - SecurityManager's actual authentication surface versus what the admin CLI expects of it, plus data governance/purge, circuit breaking, rate limiting, and the billing usage-metering stub.
- [Native Context Engine & Prompt Assembly](native-context-engine.md) - The ctypes FFI bridge to the native ice_core library versus the actual (pure-Python) prompt-assembly path used at request time, plus the ONNX embedding model and dynamic token budgeting.
- [System Architecture Overview](overview.md) - The overall shape of ICE — the FastAPI gateway process versus the in-process SDK/kernel path, how they diverge, and how a request flows end to end through prompt assembly and upstream dispatch.
- [LLM Provider Adapters](provider-adapters.md) - The core/providers/* adapter abstraction that translates inbound Anthropic/Gemini client requests into ICE's internal OpenAI-style format, and how that differs from the separate, adapter-less outbound upstream dispatch in resolve_routing.
