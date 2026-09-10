---
type: subsystem
title: Native Context Engine & Prompt Assembly
description: The ctypes FFI bridge to the native ice_core library versus the actual (pure-Python) prompt-assembly path used at request time, plus the ONNX embedding model and dynamic token budgeting.
tags: [ffi, ctypes, prompt-assembly, embeddings, onnx, token-budgeting, native-library]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-9d29e189874089ec77653e7c
    resource: repo://ice/core/pager.py
  - id: openwiki-source-040f7d98847114f8e472b3a4
    resource: repo://ice/core/rcc_ffi/ice_core.c
  - id: openwiki-source-5066621dc2f4b6ed61903250
    resource: repo://ice/core/rcc_ffi/pager.h
  - id: openwiki-source-c72a6767d16764ea1eecae02
    resource: repo://ice/core/rcc_ffi/wrapper.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Two separate "context engines" — only one is on the hot path

ICE ships two independent prompt-assembly implementations, and they are **not** the same code path:

1. **`ice/core/rcc_ffi/`** — a native C library (`ice_core.c`, built to `libice_core.so`/`.dylib`/`.dll`) loaded via `ctypes` in `ice/core/rcc_ffi/wrapper.py`, exposing `rcc_assemble_prompt`, `rcc_save_message`, `rcc_search_episodic`, `rcc_ingest_document`.
2. **`ice/core/pager.py`'s `ContextPager.assemble_prompt`** — a pure-Python implementation with its own dynamic budgeting, prompt-template selection, and truncation logic.

`ice/main.py`'s actual chat-completion path (`generate_ice_chunks`) calls `ice_server.pager.assemble_prompt(...)` — the **Python** implementation. It never calls `rcc_assemble_prompt`. The `IceMessage`/`IceVector`/`IceStringArray`/`AssembledPrompt` ctypes structures and `rcc_free_string_array`/`rcc_free_assembled_prompt` helpers imported at the top of `ice/main.py` are never instantiated or called anywhere in that module — the native prompt-assembly path is effectively dead code from the gateway's perspective, despite `ICEServer.startup()` treating a failed native-library load as a fatal, unrecoverable startup error (see [[gateway-api]]).

The only native FFI call actually exercised by the gateway is `rcc_ingest_document`, from the `POST /v1/ingest` route.

## What the native stub actually does

`ice/core/rcc_ffi/ice_core.c` is, in this tree, a stub implementation rather than a functioning "Resonant C Compiler" engine:

- **`rcc_save_message`** and **`rcc_search_episodic`** are one-line stubs that immediately `return 0;` / `return NULL;` — they perform no work.
- **`rcc_ingest_document`** likewise `return 0;` unconditionally. Since `POST /v1/ingest` in `ice/main.py` reports `chunks_ingested` directly from this return value, every ingestion request through that route reports "success" with `chunks_ingested: 0` regardless of the file's actual content — no document content is ever indexed through this path.
- **`rcc_assemble_prompt`** does perform real work, but far less than its header doc comment (`pager.h`) claims: the comment says it "assembles historical messages, retrieved RAG insights, and active reasoning traces... into a final prompt that respects the model's token limit." The implementation only concatenates `historical_messages` and `current_request` into the output array (via `strdup`); the `retrieved_insights` and `reasoning_traces` parameters are counted toward the allocated `total_capacity` but their contents are **never copied into the output**, and the `max_input_tokens`/`model_id` parameters are accepted but never read in the function body — there is no truncation or model-aware budgeting in the C implementation, contrary to the documented contract. Token counts use the same crude `strlen(content) / 4` heuristic seen elsewhere in the Python code.

## The actual assembly path: `ContextPager.assemble_prompt`

This is what runs on every real request. It does not build a `messages` array in the target LLM's native multi-turn format — it collapses everything into a **single synthetic user message** built from string templates:

1. **Budgeting** (`get_dynamic_budget`) — picks a context window by matching keywords in the model id: cloud models (`gpt-4`, `claude`, `gemini`, `sonar`, …) get 128k; local "large" models (`7b`…`32b`, `qwen3`) get 32k; local "small" models (`3b`, `ministral`, `phi`, …) get 8k; otherwise falls back to `ICE_MODEL_CONTEXT_WINDOW` (default 8192). If `ICE_POST_LIMIT` is explicitly set, it overrides model-based detection entirely.
2. **Output-budget sizing** (`get_smart_output_budget`) — scans messages newest-to-oldest for keywords (`detailed`/`comprehensive`/... → 4096 tokens reserved; `brief`/`summary`/`tl;dr`/... → 512 tokens reserved), falling back to `ICE_DEFAULT_OUTPUT_TOKENS` (default 1024) if no keyword matches or `ICE_DYNAMIC_OUTPUT_BUDGET` is disabled. "Detailed" keywords take priority over "brief" ones if both appear.
3. **Prompt template selection** — if the current user question contains the literal substrings `"exact value of"`, `"CRITICAL_OVERRIDE_CODE"`, or `"DATABASE_MIGRATION_KEY"`, a minimalist "extraction" instruction template is used instead of the normal conversational template. This mirrors the "demo hotfix" critical-memory recall lane in `EpisodicManager.search_episodic` (see [[episodic-memory]]) — both appear designed around the same benchmark/demo scenario of recalling a planted secret code across sessions.
4. **Assembly** — both templates concatenate, in order: an instruction block, a `### PROVIDED CONTEXT ###` block built from `retrieved_insights` and `reasoning_traces` (numbered fragments), and (for the conversational template only) a `### RECENT CONVERSATION ###` block built from the last 5 non-system historical messages, followed by the current question.
5. **Truncation** — if the estimated token count of the final string exceeds `effective_limit` (`total_budget` minus the reserved output budget, floored at 512), the string is hard-truncated by character count (`effective_limit * 4`) — described in the code itself as "very crude."

`estimate_tokens` uses `len(text) // 4 + 1` for text, plus fixed per-item costs for multimodal content (255 tokens/image, 512 tokens/audio clip, 2550 tokens for a 10-frame-sampled video) — not a real tokenizer count anywhere in this pipeline.

## `EmbeddingModel`

A local ONNX inference wrapper around `all-MiniLM-L6-v2` (384-dim output), used for the vector embeddings behind episodic/reasoning search (see [[episodic-memory]]):

- Model + tokenizer files are auto-downloaded from a fixed HuggingFace URL (`Xenova/all-MiniLM-L6-v2`) into `~/.cache/ice/models` on first use if not already present.
- Execution provider selection prefers CUDA when available, falling back to CPU.
- `embed()` handles multimodal list content by extracting and joining only `type: "text"` items; other modalities contribute nothing to the embedding.
- Inference failures during `__init__` (model download, ONNX session creation) are caught and logged as a warning rather than raised — `embed()` then falls back to returning a 384-dim zero vector, which is how `ICEServer.startup()` detects and flags `degraded_mode` (see [[gateway-api]]).
- `embed_async` offloads the synchronous ONNX/NumPy work to a thread via `asyncio.to_thread` to avoid blocking the FastAPI event loop.

## FFI mechanics (`wrapper.py`)

`get_lib()` searches three fixed locations for the platform-appropriate shared library name (`libice_core.so`/`.dylib`, `ice_core.dll`), caches the loaded handle in a module-level global, and declares `ctypes` `argtypes`/`restype` only for the functions it binds (`rcc_free_string_array`, `rcc_assemble_prompt`, `rcc_free_assembled_prompt`, `rcc_save_message`, `rcc_search_episodic`, `rcc_ingest_document`, `rcc_test_return`). If the library cannot be found or fails to load at any of the search paths, `get_lib()` raises `RuntimeError` — there is no pure-Python fallback for FFI-bound calls, even though (per above) the prompt-assembly hot path doesn't actually need this library to function.
