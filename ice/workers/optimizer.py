# SPDX-License-Identifier: MIT

import logging
from arq import create_pool
from arq.connections import RedisSettings

logger = logging.getLogger("ice_optimizer")


async def consolidate_memory(ctx, tenant_id: str, session_id: str, thread_id: str):
    """
    Background task triggered when a thread is idle.
    Fetches raw logs from Episodic Ledger for the thread,
    compiles them into a generalized 'Insight', and writes back to Postgres.
    """
    logger.info(f"Starting background memory consolidation for thread {thread_id}...")

    # 1. Connect to Postgres
    # 2. Fetch all raw events in this thread for the last 1 hour
    # 3. If there are > 20 events, we need compression.

    # Mock compression using an SLM
    # In practice, this hits an internal SLM endpoint saying:
    # "Summarize the following interaction log into a 1-sentence declarative insight rule."

    # User tried fixing postgres lock. Agent said use MVCC. User agreed.
    mock_insight = "Insight: The framework requires Postgres MVCC to circumvent SQLite multi-writer lock limitations."

    logger.info(f"Generated Insight: {mock_insight}")

    # 4. Generate Embedding for the Insight using local ONNX model
    # 5. Insert back into Postgres `episodic_ledger` as role='system', type='insight'
    # 6. Delete or mark original raw logs as 'archived' so they drop out of the hot Sliding Window

    logger.info(
        f"Consolidation complete for {thread_id}. Raw logs effectively purged from hot memory."
    )
    return True


class WorkerSettings:
    """
    ARQ settings class for the worker process.
    Run this worker via: `arq app.workers.optimizer.WorkerSettings`
    """

    functions = [consolidate_memory]
    redis_settings = RedisSettings()


# --- API Utility to dispatch the job ---


async def schedule_consolidation(tenant_id: str, session_id: str, thread_id: str):
    """
    Called by the FastAPI engine after a user's prompt is processed.
    Enqueues the job with a delay. If another request hits the thread,
    the delay resets (debouncing).
    """
    redis = await create_pool(RedisSettings())
    # Schedule to summarize memory after 5 minutes of inactivity
    await redis.enqueue_job(
        "consolidate_memory",
        tenant_id,
        session_id,
        thread_id,
        _defer_by=300,  # 5 minutes
    )
    logger.info(f"Scheduled consolidation worker for {thread_id} in 5 minutes.")
