---
type: subsystem
title: Episodic Memory & Reasoning Traces
description: How ICE persists and retrieves conversational history (EpisodicManager) and chain-of-thought reasoning traces (ReasoningManager), and how it strips reasoning tags from streamed LLM output.
tags: [episodic-memory, reasoning-traces, pii-scrubbing, redis-cache, postgresql, streaming]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-f0ee5b920dc27a9313f50184
    resource: repo://ice/core/episodic.py
  - id: openwiki-source-13b0bd2ac9146ecc6d68785b
    resource: repo://ice/core/reasoning.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Overview

Two managers own ICE's "long-term memory" tables, both backed by PostgreSQL with an optional Redis hot-cache layer:

- **`EpisodicManager`** (`ice/core/episodic.py`) — the `episodic_ledger` table: raw chat messages (role/content) per tenant/session/thread.
- **`ReasoningManager`** (`ice/core/reasoning.py`) — the `reasoning_traces` table: chain-of-thought steps, stored separately so unbounded "thinking" doesn't blow out the chat sliding window.

A third class in the same file, **`ReasoningExtractor`**, is unrelated to persistence — it's a streaming-safe state machine that strips `<think>`/`<ice_plan>`-style tags out of an LLM's token stream before it reaches the caller.

## EpisodicManager

### Writing: `save_message`

`save_message` always writes to Postgres first (`_save_to_db`), then optionally mirrors to an external RAG backend:

- Content chunking: if a string payload exceeds `ICE_CHUNK_SIZE` (default 8000 chars), it's split into overlapping chunks (`ICE_CHUNK_OVERLAP`, default 500) and each chunk is saved as a separate row tagged with `segment`/`total_segments` metadata.
- Missing embeddings (e.g. degraded mode with no embedding model available) fall back to a 384-dim zero vector rather than failing the write.
- `privacy_masking="strict"` runs `scrub_pii()` — a set of regexes for SSN, credit card, email, and North-American phone patterns — over the content before it's persisted.
- If `RAG_MODE=external`, the same content is additionally pushed to `RAGBackend.save_context` for external indexing (see [[ingestion-and-rag]]).
- `_save_to_db` also opportunistically caches the last 50 messages per `tenant_id:user_id:session_id` in Redis (`history:` key prefix, 1-hour TTL) so `get_history` can skip Postgres on the hot path.

### Reading: `get_history`

Checks the Redis cache first; only falls back to a Postgres `ORDER BY created_at ASC LIMIT` query on a cache miss. Content that looks like serialized JSON (starts with `[` or `{`) is opportunistically deserialized back into structured multimodal content.

### Search: `search_local_episodic` and `search_episodic`

`search_local_episodic` is a single pgvector cosine-distance (`<=>`) query scoped to `tenant_id`/`user_id`, used both directly and as the local leg of `search_episodic`.

`search_episodic` is the richer, multi-phase retrieval path used for prompt assembly, and layers several result sources before returning the merged, deduplicated top-`limit`:

1. **Priority tool results** — the 5 most recent `role='tool'` messages for the *current session*, prefixed `[PRIORITY ACTION RESULT]`, to keep multi-step tool-calling agents from losing track of recent tool output.
2. **"Demo hotfix" critical-memory lane** — a `LIKE`-based scan (not vector search) across *all* the user's sessions for content containing the literal substrings `CRITICAL INSTRUCTION`, `SYSTEM FACT`, or `CRITICAL_OVERRIDE_CODE`, prefixed `[CRITICAL MEMORY]` and inserted at the front of the result list. This intentionally has no `session_id` filter, so a fact planted in one session surfaces in every later session for that user.
3. **Local vector search** — `search_local_episodic`.
4. **Federated search to peer ICE nodes** — if `ICE_PEER_NODES` (comma-separated URLs) and `ICE_INTERNAL_API_KEY` are set, the same query is fanned out concurrently via `httpx` to each peer's `/v1/internal/search` endpoint (see `ice/main.py`), with W3C trace-context headers injected via `opentelemetry.propagate.inject` for distributed tracing continuity. Peer failures/timeouts (5s each) are swallowed with a warning log, not raised.

Final results are deduplicated by exact string match and truncated to `limit`; there is no cross-source re-ranking by relevance score, only the deterministic ordering established by the phases above.

### Token accounting and retention

- `get_session_token_count` approximates tokens as `SUM(LENGTH(content)) / 4` — a rough char-to-token heuristic, not a real tokenizer count.
- `purge_expired_ledger(retention_days)` finds sessions with rows older than the retention window, and if `ICE_PRE_PURGE_WEBHOOK_URL` is set, POSTs the full session history to that webhook as a `PRE_PURGE_ARCHIVE` event *before* deleting — and skips the delete entirely if the webhook call fails or errors, so archiving failure blocks purge rather than silently losing data.

## ReasoningManager

Structurally mirrors `EpisodicManager` but targets `reasoning_traces` instead of `episodic_ledger`, with one difference in cache ordering: `save_trace` uses `redis.lpush` (prepend) and trims to the last 10 entries, so the Redis-cached list is newest-first; `get_active_chain` reverses it back to chronological order before returning, both on the cache-hit and the DB-fallback path (where it also opportunistically repopulates the cache).

`save_trace` also mirrors to the external RAG backend when `RAG_MODE=external`, tagging the content with role `"reasoning"` instead of the message's actual role.

`purge_expired_traces` follows the same pre-purge-webhook-then-delete pattern as the episodic ledger, with `data_type: "reasoning"` in the payload.

Neither manager enforces retention automatically — `purge_expired_ledger`/`purge_expired_traces` must be invoked by an external scheduler; see `ice/core/governance.py` for the related on-demand `purge_data` (full tenant/user erasure) in [[multi-tenant-security]].

## ReasoningExtractor

A byte-stream state machine used by the gateway to strip internal-reasoning tags (default: `thought`, `think`, `ice_plan`, in either `<tag>...</tag>` or `[tag]...[/tag]` form) out of streamed completions before they reach the client, while still capturing the extracted content for logging/telemetry.

- `process_chunk(delta)` is called once per streamed token/delta; it buffers up to `lookahead_size` (20) characters whenever the tail of the buffer could be the start of a recognized tag, so a tag split across two network chunks is still detected correctly.
- State is binary: `0` (forwarding — output passes through) or `1` (buffering — output is being captured inside a detected tag).
- `flush()` must be called at end-of-stream to emit any content still sitting in the buffers; if the stream ended mid-tag, the partially-captured content is still surfaced as an "unfinished" extraction rather than dropped.

This class has no persistence dependency — it's pure text-stream processing, safe to instantiate per-request.

## Security dependency

Both managers call `SecurityManager.safe_uuid(tenant_id)` on every query to coerce/validate the tenant identifier before it reaches SQL — see [[multi-tenant-security]] for what that guards against.
