<!-- Draft. Not published. No real data yet -- see "What's needed" below. -->

# PostgreSQL-only storage architecture

**Status: blocked on real data. Same caveat as SAR-124 — the hook numbers
(93,251 msg/s, 8µs p50 save_message, sub-0.01ms cache hit, 27% faster than
Redis, 40% infra cost reduction) don't appear anywhere in this repo's real
benchmark results. These are targets from the ticket spec, not measurements.**

## What this post needs that doesn't exist yet

1. Two comparable deployments: the current Redis-backed stack (pub/sub,
   cache, distributed locks) and a PostgreSQL-only stack (pgvector HNSW,
   advisory locks, an in-process LRU, `LISTEN`/`NOTIFY`) — same hardware,
   same workload.
2. A write-throughput load test (messages/sec) and a p50/p99 latency
   breakdown for `save_message`, run against both.
3. A real cost comparison (infra spend before/after) — not something a
   benchmark script produces on its own; needs actual deployment cost data.

This is entirely outside `benchmarks/` — it's a real infrastructure load
test against two different deployment topologies, not a config swap on the
existing sandboxed harness.

## What we do have

Nothing directly. `docs/legacy/operations/BENCHMARKS.md` contains
similar-shaped throughput/latency claims but is the same unverified-marketing
lineage flagged in SAR-124 — not a source to draw from here.

**Platforms**: LinkedIn (doc/PDF) + Reddit r/LocalLLaMA + r/VibeCoding.
