<!-- Draft. Not published. No real data yet -- see "What's needed" below. -->

# Turn-granular indexing architecture

**Status: blocked on real data. Do not publish the ticket's hook numbers
(8µs write latency, 93k msg/s on PostgreSQL) — they don't appear anywhere in
this repo's benchmark results. Grepped for the exact figures; nothing.
`docs/legacy/operations/BENCHMARKS.md` has similar-shaped claims (different
numbers) but is the same lineage of unverified marketing copy this project's
own `blog-draft.md` already disclaims ("not produced by this harness and
are not repeated here").**

## What this post needs that doesn't exist yet

This is a systems/infra post, not something `benchmarks/` (which runs ICE in
`sandbox` mode against in-memory aiosqlite, specifically to avoid needing
Postgres) can produce. To get real numbers:

1. A running PostgreSQL 16+ instance with pgvector + HNSW configured
   (`efConstruction`/`M`/`efSearch` values need to be picked and recorded).
2. ICE running in `production` mode against it (not `sandbox`).
3. A write-path load test instrumenting `save_message` end to end: embed →
   pgvector insert → HNSW index update → commit, with latency captured at
   each stage.
4. A real comparison run: turn-granular indexing vs sliding-window/fixed-chunk,
   on the same data, same hardware, for the recall/latency/storage numbers
   the post wants.

None of this exists in the current benchmark harness. It's a separate
build — a load-test script plus real Postgres infra — not a config change.

## What we do have

Turn-granular indexing's *retrieval* advantage is already demonstrated
indirectly in SAR-117/123 (LoCoMo vs MemPalace): MemPalace embeds whole
sessions, ICE embeds individual turns, and ICE wins R@5 by +44%. That's a
real, measured proxy for "turn granularity helps," even though it doesn't
touch write-latency/throughput at all.

**Platforms**: LinkedIn + Reddit r/LocalLLaMA + r/VibeCoding.
