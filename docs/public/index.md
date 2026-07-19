# ICE V3: The Local-Tier Cognitive OS

ICE V3 is not a vector database or a RAG pipeline; it is a **pure, embedded, physics-native memory engine for Large Language Models.** It provides a Local-Tier, high-performance VMM (Virtual Memory Management) layer that you mount directly into your application.

This allows you to give any LLM a functionally indexless context window, with memory retrieval speeds measured in microseconds.

## Core Principles
1.  **Local-Tier & Embedded:** ICE runs entirely within your application. There is no external server, no network latency, and your data never leaves your environment.
2.  **Physics-Native Performance:** The core memory operations are handled by a pre-compiled, optimized binary kernel, bypassing the overhead of standard Python for critical tasks.
3.  **Gold Standard DX:** The SDK is 100% type-safe, providing a clean, intuitive, and Production-grade developer experience.

## Next Steps
- **[Quickstart](./quickstart.md):** Get up and running in 60 seconds.
- **[Customization](./customization.md):** Learn how to fine-tune the engine's physics.
- **[Production Integration](./escape_hatches.md):** Discover how to use middleware and custom transports.
