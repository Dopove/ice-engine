---
type: subsystem
title: Document Ingestion & RAG Pipeline
description: IngestionPipeline's multimodal document pipeline and the external RAGBackend mirror — both broken by method-name mismatches against EpisodicManager — plus the unrelated MemoryStore used by ICEWrapper and the unused StorageManager abstraction.
tags: [ingestion, rag, multimodal, storage, lazy-loading]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-f0ee5b920dc27a9313f50184
    resource: repo://ice/core/episodic.py
  - id: openwiki-source-24f3592ebc2a12e285edd84d
    resource: repo://ice/core/ingestion.py
  - id: openwiki-source-13b0bd2ac9146ecc6d68785b
    resource: repo://ice/core/reasoning.py
  - id: openwiki-source-a55fb6b5392625c6467277a3
    resource: repo://ice/core/storage.py
  - id: openwiki-source-cd241d204bf0c49f44c0a3a9
    resource: repo://ice/rag/backend.py
  - id: openwiki-source-ecda5ab2a5d26aabcc134de4
    resource: repo://ice/sdk.py
  - id: openwiki-source-c14131ca5a306d4f3746920d
    resource: repo://ice/store/base.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## `IngestionPipeline` (`ice/core/ingestion.py`)

Intended to bridge the optional `RAGAnything` multimodal pipeline (parsing PDFs, images, tables, equations) into ICE's episodic memory. `RAGAnything`/`RAGAnythingConfig` are loaded lazily via `OptionalModule("raganything", "multimodal")` (`ice/core/lazy.py`) — a thin wrapper that defers `__import__` until first attribute access, raising a friendlier `ImportError` ("install it using: pip install ice-engine[multimodal]") than a raw missing-module traceback would.

Configuration (`_load_multimodal_config`) merges hardcoded env-var defaults (`ICE_RAG_PARSER=docling`, image/table/equation processing toggles) with an optional deep-merge from a JSON file at `ICE_RAG_CONFIG_FILE`, if set and present.

**`ingest_document` is broken against the rest of the tree in two ways:**

1. It never actually reads the file at `file_path`. `ice/core/storage.py`'s `StorageManager` (a real local/S3/GCS/fsspec-backed path abstraction with `is_remote_path`, `exists`, `list_files`, `fetch_to_local`) is imported at the top of `ingestion.py` (`from .storage import StorageManager`) but never referenced anywhere in the class body. Instead, `ingest_document` synthesizes a placeholder string — `f"Processed {file_path} using RAG-Anything"` — and persists *that* literal string as the "processed content," regardless of what the file actually contains. The lazily-loaded `RAGAnything` instance is constructed (triggering the lazy-load and thus the `pip install ice-engine[multimodal]` error if unavailable) but its result is never used either.
2. It calls `self.episodic.save(tenant_id=..., user_id=..., session_id=..., role=..., content=..., metadata=...)`. `EpisodicManager` (see [[episodic-memory]]) has no `save` method — only `save_message`, with a different parameter set (positional `tenant_id, session_id, role, content`, and no `session_id=context_id` keyword form). Every call to `ingest_document` raises `AttributeError: 'EpisodicManager' object has no attribute 'save'`.

**Separately, the SDK's advertised ingestion entrypoint calls a method that doesn't exist on this class at all.** `ice/sdk.py`'s `IndexlessContextClient.ingest` (the "[DX] One-line multimodal ingestion" method — see [[sdk-and-clients]]) calls `self.kernel.ingestion.ingest_path(tenant_id=..., user_id=..., path=...)`. `IngestionPipeline` defines `__init__`, `_load_multimodal_config`, `_get_rag_instance`, and `ingest_document` — there is no `ingest_path` method. Both the SDK's `client.ingest(...)` and the `ice mount` CLI command (`ice/cli.py`, which calls `ice_client.ingest(...)` after `await init()`) route through this call and would raise `AttributeError` before reaching `ingest_document` at all — independent of, and in addition to, `ingest_document`'s own gaps above.

## External RAG mirror: `RAGBackend` (`ice/rag/backend.py`)

When `RAG_MODE=external`, `EpisodicManager.save_message` and `ReasoningManager.save_trace` (see [[episodic-memory]]) each construct `RAGBackend(mode=rag_mode, tenant_id=tenant_id)` and call `await backend.save_context(tenant_id, session_id, role, content)` to mirror data into an external RAG system, in addition to the local Postgres write.

**This call path is also broken, independently of the `IngestionPipeline` issues above:**

- `RAGBackend.__init__(self, config=None)` accepts only an optional `config` dict — it does not accept `mode` or `tenant_id` keyword arguments. Constructing `RAGBackend(mode=rag_mode, tenant_id=tenant_id)` raises `TypeError` immediately.
- Even setting that aside, `RAGBackend` defines only `query` (a stub that always returns `[]`) and `index_document` (a stub that only logs and does nothing) — there is no `save_context` method at all. The call `backend.save_context(...)` would raise `AttributeError` even against a correctly-constructed instance.

In practice, this means setting `RAG_MODE=external` — the "ICE Cloud" architecture mode logged at startup in `ICEServer.startup()` (see [[gateway-api]]) — currently breaks every episodic save and reasoning-trace save in the request path, since both call sites hit this broken construction unconditionally whenever that mode is active.

## `MemoryStore` (`ice/store/base.py`) — a different, working component

Despite the name suggesting a general storage abstraction, `ice/store/base.py`'s `MemoryStore` is a small, self-contained local memory backend: it lazily opens a DuckDB file (default `~/.ice/ice_memory.db`) and exposes `save(role, content, metadata=None)` / `retrieve(query)` (the `query` argument is currently unused — `retrieve` always returns the 5 most recent rows ordered by timestamp, with no actual query filtering). It is used exclusively by `ICEWrapper`'s `ChatProxy` (see [[overview]] and [[sdk-and-clients]]) as the memory backing for the "3-line drop-in" wrapper pattern — it is unrelated to `IngestionPipeline`/`RAGBackend` and does not participate in the gateway's episodic/reasoning pipeline at all.

`_init_db`'s `except ImportError` (falling back to "Local memory will be volatile" logging) is effectively dead code: `duckdb` is imported unconditionally at the top of the module (`import duckdb`), so if the package isn't installed, importing `ice/store/base.py` itself fails before `_init_db` — or any other method — can ever run.

## `StorageManager` (`ice/core/storage.py`) — imported but unused

A real, functioning `fsspec`-backed abstraction over local filesystem, S3, GCS, and other S3-compatible stores (`is_remote_path`, `is_dir`, `exists`, `list_files`, `fetch_to_local`), with an explicit, hardcoded rejection of Azure Blob Storage URLs (`abfs://`, `az://`) via `_check_protocol`. Despite being imported into `ingestion.py`, nothing in this tree actually calls any of its methods — `IngestionPipeline.ingest_document` does not use it to read the file it's meant to ingest (see above). As it stands, `StorageManager` is a complete, working component with no caller.
