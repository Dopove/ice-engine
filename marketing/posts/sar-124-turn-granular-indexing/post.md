<!-- Draft. Not published. Real single-write persist latency now captured against
genuine AWS RDS; per-stage breakdown and the sliding-window comparison run are
still outstanding -- see "What we now have" below. -->

# Turn-granular indexing architecture

**Status: partially unblocked. Do not publish the ticket's hook numbers
(8µs write latency, 93k msg/s on PostgreSQL) — they don't appear anywhere in
this repo's benchmark results. Those are ticket-spec targets, not
measurements. `docs/legacy/operations/BENCHMARKS.md` has similar-shaped
claims (different numbers) but is the same lineage of unverified marketing
copy this project's own `blog-draft.md` already disclaims ("not produced by
this harness and are not repeated here").**

## What we now have (2026-09-19, real AWS RDS)

Ran ICE in `production` mode (no Redis — `REDIS_URL` unset) against a real
`db.t4g.micro` PostgreSQL 16 + pgvector instance on AWS RDS, connecting as
the least-privilege `ice_app_user` role `setup_db.py` provisions (RLS +
`FORCE ROW LEVEL SECURITY` enforced, not the admin/owner role). This is
genuine end-to-end Postgres persistence for `save_message`, not the
sandbox/in-memory-aiosqlite path.

- `save_message` end-to-end persist latency (embed → pgvector insert →
  commit, single writer, n=200 per run, two independent runs): mean
  676.7–709.8ms, p50 669.9–693.3ms, p95 676.9–706.9ms, p99 713.8–1852ms.
- **Caveat — do not publish this as a production latency number.** It was
  measured over a public WAN link (this machine to `us-east-1`), not
  same-VPC. It proves real persistence works end to end and bounds
  order-of-magnitude cost; a same-region/same-VPC deployment will be
  meaningfully faster.
- Burst/concurrent-write throughput and a per-stage (embed vs. insert vs.
  HNSW update) latency breakdown were attempted but the results aren't
  usable: CloudWatch showed the RDS instance itself was not CPU- or
  credit-constrained during the test window, while `DatabaseConnections`
  oscillated erratically (including several consecutive zero-connection
  minutes) — evidence of an unstable path from this machine to AWS, not an
  ICE or Postgres limitation. Re-run from a same-region client (EC2 or a CI
  runner in `us-east-1`) before publishing any throughput or per-stage
  number.

## What this post still needs

1. A per-stage latency breakdown (embed / pgvector insert / HNSW index
   update / commit) — needs a same-region client to get a trustworthy
   number; the WAN run above only has the aggregate.
2. A real comparison run: turn-granular indexing vs. sliding-window/
   fixed-chunk, on the same data, same hardware, for the recall/latency/
   storage numbers the post wants. Not attempted yet.

## What we do have

Turn-granular indexing's *retrieval* advantage is already demonstrated
indirectly in SAR-117/123 (LoCoMo vs MemPalace): MemPalace embeds whole
sessions, ICE embeds individual turns, and ICE wins R@5 by +44%. That's a
real, measured proxy for "turn granularity helps," even though it doesn't
touch write-latency/throughput at all.

**Platforms**: LinkedIn + Reddit r/LocalLLaMA + r/VibeCoding.
