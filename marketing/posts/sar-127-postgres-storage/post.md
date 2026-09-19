<!-- Draft. Not published. Real single-write persist latency and a validated
Postgres-native distributed lock now exist for the Postgres-only side; the
Redis-backed comparison run and cost data are still outstanding -- see "What
we now have" below. -->

# PostgreSQL-only storage architecture

**Status: partially unblocked. Same caveat as SAR-124 — the hook numbers
(93,251 msg/s, 8µs p50 save_message, sub-0.01ms cache hit, 27% faster than
Redis, 40% infra cost reduction) don't appear anywhere in this repo's real
benchmark results. These are ticket-spec targets, not measurements.**

## What we now have (2026-09-19, real AWS RDS)

The Postgres-only stack this post describes now actually exists and runs:
`RedisDistributedSemaphore` is backed by a new `PostgresDistributedSemaphore`
(session-level advisory locks) when `REDIS_URL` is unset, wired into both the
stitch-concurrency limiter and node-count license enforcement, which
previously either fell back to a non-distributed in-process semaphore or
silently skipped enforcement entirely without Redis. 4/4 new integration
tests plus the existing Wave-3 Redis-removal parity suite pass against a real
Postgres container.

Ran this Postgres-only build (no Redis) against real AWS RDS
(`db.t4g.micro`, Postgres 16 + pgvector), as the least-privilege
`ice_app_user` role with RLS/`FORCE ROW LEVEL SECURITY` enforced:

- `save_message` end-to-end persist latency, single writer, n=200 per run,
  two independent runs: mean 676.7–709.8ms, p50 669.9–693.3ms, p95
  676.9–706.9ms, p99 713.8–1852ms. **Measured over a public WAN link
  (this machine to `us-east-1`), not same-VPC — do not publish as a
  production number.**
- Concurrent-write throughput and `PostgresDistributedSemaphore`
  contention-under-load numbers were attempted on the same RDS instance but
  aren't trustworthy: CloudWatch showed the instance itself was not CPU- or
  credit-constrained during the test window, while `DatabaseConnections`
  oscillated erratically (including several consecutive zero-connection
  minutes) — pointing to an unstable network path from this machine, not a
  Postgres-only architecture limit. Re-run from a same-region client before
  publishing any throughput or contention number.

## What this post still needs

1. A comparable Redis-backed stack run from the same location, same
   workload, so the WAN-latency numbers above are an apples-to-apples
   comparison rather than a standalone figure. Not attempted yet.
2. Trustworthy concurrent-write throughput and lock-contention numbers from
   a same-region client (EC2 or CI runner in `us-east-1`).
3. A real cost comparison (infra spend before/after) — not something a
   benchmark script produces on its own; needs actual deployment cost data.

## What we do have otherwise

`docs/legacy/operations/BENCHMARKS.md` contains similar-shaped
throughput/latency claims but is the same unverified-marketing lineage
flagged in SAR-124 — not a source to draw from here.

**Platforms**: LinkedIn (doc/PDF) + Reddit r/LocalLLaMA + r/VibeCoding.
