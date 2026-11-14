#!/usr/bin/env python3
"""
RDS validation — genuinely Postgres-only ICE (no Redis), real network latency.

Validates the rebuild from commit 8d5a0e27 (PostgresDistributedSemaphore +
the fixed register_node()/health-check fallbacks + the setup_db.py
reasoning_traces schema fix) against a real AWS RDS Postgres instance,
not the throwaway local container used for correctness testing.

Measures, with redis_client=None / ICE_USE_ARQ=0 throughout:
  - save_message  raw persist latency (p50/p95/p99), N=200
  - save_trace    raw persist latency (p50/p95/p99), N=200
  - burst write throughput: 20 concurrent writers x 25 messages = 500 writes
  - PostgresDistributedSemaphore acquire/release latency under contention

Run:
  ICE_RDS_DSN=postgresql://user:pass@host:5432/db \
    .venv/bin/python benchmarks/scripts/rds_postgres_only_validation.py
"""

import asyncio
import os
import statistics
import sys
import time
import uuid

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ice.core.episodic import EpisodicManager
from ice.core.reasoning import ReasoningManager
from ice.core.distributed_semaphore import PostgresDistributedSemaphore
from ice.core.tenant_scope import tenant_conn

DSN = os.environ["ICE_RDS_DSN"]
TENANT = str(uuid.uuid4())


def summarize(name, lat):
    if not lat:
        print(f"  {name:<30} no samples")
        return None
    s = sorted(lat)
    mean = statistics.mean(lat)
    p50 = s[len(s) // 2]
    p95 = s[min(len(s) - 1, int(0.95 * len(s)))]
    p99 = s[min(len(s) - 1, int(0.99 * len(s)))]
    print(
        f"  {name:<30} mean={mean*1000:8.3f}ms  "
        f"p50={p50*1000:8.3f}  p95={p95*1000:8.3f}  p99={p99*1000:8.3f}  (n={len(lat)})"
    )
    return {"mean_ms": mean * 1000, "p50_ms": p50 * 1000, "p95_ms": p95 * 1000, "p99_ms": p99 * 1000, "n": len(lat)}


async def ensure_tenant(pool):
    # tenant_self_policy (setup_db.py) requires ice.current_tenant_id to equal
    # the row being inserted -- tenant_conn sets it to TENANT itself, matching
    # how setup_db.py bootstraps its own default tenant row.
    async with tenant_conn(pool, TENANT) as conn:
        await conn.execute(
            "INSERT INTO tenants (tenant_id, name, api_key) VALUES ($1,$2,$3) "
            "ON CONFLICT DO NOTHING",
            TENANT, "rds-validation", f"bench-{uuid.uuid4().hex[:8]}",
        )


async def persist_latency_test(pool):
    print("\n== SAVE_MESSAGE raw persist latency (Postgres-only, real RDS) ==")
    epi = EpisodicManager(pool, redis_client=None)
    session = f"persist-{uuid.uuid4().hex[:8]}"
    lat = []
    for _ in range(200):
        t0 = time.perf_counter()
        await epi._save_to_db(
            TENANT, session, "t1", "user", "benchmark message — some payload content",
            None, "persist-user", {},
        )
        lat.append(time.perf_counter() - t0)
    return summarize("save_message persist", lat)


async def reasoning_latency_test(pool):
    print("\n== SAVE_TRACE raw persist latency (Postgres-only, real RDS) ==")
    rea = ReasoningManager(pool, redis_client=None)
    session = f"reason-{uuid.uuid4().hex[:8]}"
    lat = []
    for i in range(200):
        t0 = time.perf_counter()
        await rea._save_to_db(
            TENANT, session, f"reasoning step {i}", "t1", "reason-user",
            None, i, None, None,
        )
        lat.append(time.perf_counter() - t0)
    return summarize("save_trace persist", lat)


async def burst_test(pool):
    print("\n== BURST throughput: 20 concurrent x 25 writes (Postgres-only) ==")
    # save_message() is fire-and-forget by design (asyncio.create_task, not
    # awaited -- the hot Redis path is meant to return before the cold
    # Postgres flush lands). Measuring wall time around save_message() calls
    # therefore times enqueueing, not persistence, and against real RDS
    # network latency (~700ms/write, see persist_latency_test above) that
    # made 500 orphaned background tasks outlive burst_test() and get killed
    # mid-write when the script's pool.close() ran -- a real gap this
    # exposed: no backpressure/queue limit on fire-and-forget persistence
    # when ARQ/Redis aren't present to absorb the burst. Calling _save_to_db
    # directly here awaits genuine persistence, giving an honest concurrent
    # throughput number instead of an enqueue-rate one.
    N_CONCURRENT = 20
    M_PER_WORKER = 25
    session = f"burst-{uuid.uuid4().hex[:8]}"
    epi = EpisodicManager(pool, redis_client=None)
    errors = []

    async def writer(w):
        try:
            for i in range(M_PER_WORKER):
                await epi._save_to_db(
                    TENANT, session, "t1", "user", f"burst msg w{w}-{i}",
                    None, "burst-user", {},
                )
        except Exception as e:  # noqa: BLE001
            errors.append((w, repr(e)))

    t0 = time.perf_counter()
    await asyncio.gather(*[writer(w) for w in range(N_CONCURRENT)])
    t_write = time.perf_counter() - t0

    async with tenant_conn(pool, TENANT) as conn:
        landed = await conn.fetchval(
            "SELECT COUNT(*) FROM episodic_ledger WHERE tenant_id=$1 AND session_id=$2",
            TENANT, session,
        )
    total = N_CONCURRENT * M_PER_WORKER
    throughput = total / t_write
    print(f"  total writes:     {total}")
    print(f"  wall time:        {t_write:.3f}s")
    print(f"  throughput:       {throughput:.1f} msg/s")
    print(f"  landed in PG:     {landed}/{total}")
    print(f"  errors:           {len(errors)}")
    return {"total": total, "wall_s": t_write, "msg_per_s": throughput, "landed": landed, "errors": len(errors)}


async def semaphore_contention_test(pool):
    print("\n== PostgresDistributedSemaphore acquire/release under contention ==")
    name = f"bench-sem-{uuid.uuid4().hex[:8]}"
    limit = 3
    n_workers = 12
    lat = []
    lock = asyncio.Lock()
    peak = 0
    live = 0

    async def worker():
        nonlocal peak, live
        sem = PostgresDistributedSemaphore(pool, name, limit)
        t0 = time.perf_counter()
        await sem.acquire()
        lat.append(time.perf_counter() - t0)
        async with lock:
            live += 1
            peak = max(peak, live)
        await asyncio.sleep(0.02)
        async with lock:
            live -= 1
        await sem.release()

    t0 = time.perf_counter()
    await asyncio.gather(*[worker() for _ in range(n_workers)])
    t_total = time.perf_counter() - t0
    print(f"  peak concurrent holders: {peak} (limit={limit})")
    print(f"  total wall time:         {t_total:.3f}s")
    result = summarize("acquire latency", lat)
    return {"peak_holders": peak, "limit": limit, "wall_s": t_total, "acquire_latency": result}


async def main():
    pool = await asyncpg.create_pool(dsn=DSN, min_size=5, max_size=25)
    try:
        print(f"Connected to RDS. Tenant: {TENANT}")
        await ensure_tenant(pool)
        results = {}
        results["save_message_persist"] = await persist_latency_test(pool)
        results["save_trace_persist"] = await reasoning_latency_test(pool)
        results["burst"] = await burst_test(pool)
        results["semaphore_contention"] = await semaphore_contention_test(pool)

        print("\n=== SUMMARY (JSON) ===")
        import json
        print(json.dumps(results, indent=2))
    finally:
        async with tenant_conn(pool, TENANT) as conn:
            await conn.execute("DELETE FROM episodic_ledger WHERE tenant_id=$1", TENANT)
            await conn.execute("DELETE FROM reasoning_traces WHERE tenant_id=$1", TENANT)
            await conn.execute("DELETE FROM tenants WHERE tenant_id=$1", TENANT)
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
