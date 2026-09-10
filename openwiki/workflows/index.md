# Files

- [Document Ingestion & RAG Pipeline](ingestion-and-rag.md) - IngestionPipeline's multimodal document pipeline and the external RAGBackend mirror — both broken by method-name mismatches against EpisodicManager — plus the unrelated MemoryStore used by ICEWrapper and the unused StorageManager abstraction.
- [SDK, Wrapper & Client Libraries](sdk-and-clients.md) - The three in-process consumption surfaces — ice/sdk.py's IndexlessContextClient, ice/wrapper.py's drop-in ICEWrapper, and the Node.js bridge/native-addon pair — and how the Node.js package is disconnected from the Python bridge it appears to pair with.
- [Telemetry & Observability Pipeline](telemetry.md) - The gateway's direct OTel SDK wiring versus the ice/telemetry/* package (RemoteTelemetryClient, TelemetryMiddleware, privacy redaction) — the latter fails to import in the current environment, and its privacy allowlist would drop nearly all payload content even if it did.
