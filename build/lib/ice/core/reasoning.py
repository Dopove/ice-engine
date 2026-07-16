import logging
from typing import List, Optional, Dict, Any
import uuid
from opentelemetry import trace # Add OpenTelemetry import
from .security import SecurityManager

logger = logging.getLogger("ice_reasoning")
tracer = trace.get_tracer(__name__) # Initialize tracer

class ReasoningManager:
    """
    Manages deep reasoning traces (Chain-of-Thought) for ICE threads.
    Reasoning traces are stored separately from chat history to allow
    for unbounded 'thinking' without blowing out the sliding window.
    """

    def __init__(self, db_pool, redis_client=None):
        self.db_pool = db_pool
        self.redis = redis_client

    async def _save_to_db(
        self,
        tenant_id: str,
        session_id: str,
        content: str,
        thread_id: Optional[str],
        user_id: str,
        parent_trace_id: Optional[str],
        step_number: Optional[int],
        metadata: Optional[Dict[str, Any]],
        embedding: Optional[List[float]],
    ):
        """Helper to save a reasoning trace to the local PostgreSQL database."""
        import json
        async with self.db_pool.acquire() as conn:
            query = """
                INSERT INTO reasoning_traces (
                    tenant_id, session_id, thread_id, user_id, parent_trace_id, content, embedding, step_number, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, created_at
            """
            row = await conn.fetchrow(
                query,
                SecurityManager.safe_uuid(tenant_id),
                session_id,
                thread_id,
                user_id,
                uuid.UUID(parent_trace_id) if parent_trace_id else None,
                content,
                embedding,
                step_number,
                json.dumps(metadata) if metadata else "{}",
            )
            return row["id"], row["created_at"]

    @tracer.start_as_current_span("ReasoningManager.save_trace")
    async def save_trace(
        self,
        tenant_id: str,
        session_id: str,
        content: str,
        thread_id: Optional[str] = None,
        user_id: str = "default-user",
        parent_trace_id: Optional[str] = None,
        step_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ):
        """
        Saves a reasoning step to the database and updates the Redis cache.
        """
        if not self.db_pool:
            logger.warning("DB pool not available in ReasoningManager, cannot save trace.")
            return None

        # 1. Save to local PostgreSQL
        trace_id, created_at = await self._save_to_db(
            tenant_id, session_id, content, thread_id, user_id, parent_trace_id, step_number, metadata, embedding
        )

        # 2. Update Redis cache
        if self.redis:
            import json
            cache_key = f"reasoning:{tenant_id}:{user_id}:{session_id}"
            trace_dict = {
                "content": content,
                "step_number": step_number,
                "metadata": metadata or {},
                "created_at": created_at.isoformat(),
            }
            # Prepend to list to keep recent ones at the start
            await self.redis.lpush(cache_key, json.dumps(trace_dict))
            # Keep only the last 10 traces
            await self.redis.ltrim(cache_key, 0, 9)
            # Set TTL to 1 hour
            await self.redis.expire(cache_key, 3600)

        # 3. [HYENA FEATURE]: Save to External RAG Backend if configured
        import os
        rag_mode = os.getenv("RAG_MODE", "local")
        if rag_mode == "external":
            from ice.rag.backend import RAGBackend
            backend = RAGBackend(mode=rag_mode, tenant_id=tenant_id)
            await backend.save_context(tenant_id, session_id, "reasoning", content)

        return trace_id

    @tracer.start_as_current_span("ReasoningManager.get_active_chain")
    async def get_active_chain(
        self, tenant_id: str, session_id: str, user_id: str = "default-user", limit: int = 10, conn=None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent reasoning steps for JIT context.
        Prioritizes low-latency Redis cache before hitting Postgres.
        """
        import json

        if self.redis:
            cache_key = f"reasoning:{tenant_id}:{user_id}:{session_id}"
            cached_traces = await self.redis.lrange(cache_key, 0, limit - 1)
            if cached_traces:
                # The stored sequence is newest first (from lpush).
                # We usually want to return chronological (oldest first for prompt assembly)
                parsed = [json.loads(t) for t in cached_traces]
                return list(reversed(parsed))

        # Fallback to DB
        query = """
            SELECT content, step_number, metadata, created_at
            FROM reasoning_traces
            WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3
            ORDER BY created_at DESC
            LIMIT $4
        """
        
        if conn:
            rows = await conn.fetch(query, SecurityManager.safe_uuid(tenant_id), user_id, session_id, limit)
        else:
            async with self.db_pool.acquire() as pool_conn:
                rows = await pool_conn.fetch(query, SecurityManager.safe_uuid(tenant_id), user_id, session_id, limit)

        # Opportunistically populate empty cache
        if self.redis and rows:
            cache_key = f"reasoning:{tenant_id}:{user_id}:{session_id}"
            for r in rows:  # rows are already newest first
                trace_dict = {
                    "content": r["content"],
                    "step_number": r["step_number"],
                    "metadata": json.loads(r["metadata"])
                    if isinstance(r["metadata"], str)
                    else r["metadata"],
                    "created_at": r["created_at"].isoformat(),
                }
                await self.redis.rpush(
                    cache_key, json.dumps(trace_dict)
                )  # Maintain newest first ordering locally
            await self.redis.expire(cache_key, 3600)

        return [dict(r) for r in reversed(rows)]  # Return in chronological order

    @tracer.start_as_current_span("ReasoningManager.search_reasoning")
    async def search_reasoning(
        self, tenant_id: str, query_vector: list[float], user_id: str = "default-user", limit: int = 20, conn=None
    ) -> list[str]:

        """
        Semantic search over historical reasoning traces.
        """
        search_query = """
            SELECT content
            FROM reasoning_traces
            WHERE tenant_id = $1 AND user_id = $2
            ORDER BY embedding <=> $3::vector
            LIMIT $4
        """
        if conn:
            rows = await conn.fetch(search_query, SecurityManager.safe_uuid(tenant_id), user_id, str(query_vector), limit)
        else:
            async with self.db_pool.acquire() as pool_conn:
                rows = await pool_conn.fetch(search_query, SecurityManager.safe_uuid(tenant_id), user_id, str(query_vector), limit)
        return [r["content"] for r in rows]

    @tracer.start_as_current_span("ReasoningManager.purge_expired_traces")
    async def purge_expired_traces(self, retention_days: int):
        """
        [ENTERPRISE COMPLIANCE]
        Removes reasoning traces older than the configured retention period.
        Supports Pre-Purge Webhook for cold storage archiving.
        """
        import os
        import json
        import httpx
        webhook_url = os.getenv("ICE_PRE_PURGE_WEBHOOK_URL")

        async with self.db_pool.acquire() as conn:
            # 1. Identify expired trace sessions
            rows = await conn.fetch("SELECT DISTINCT tenant_id, user_id, session_id FROM reasoning_traces WHERE created_at < NOW() - make_interval(days := $1)", retention_days)

            for row in rows:
                t_id, u_id, s_id = row["tenant_id"], row["user_id"], row["session_id"]

                # 2. Archiving logic
                if webhook_url:
                    try:
                        # Fetch traces for this session
                        traces = await conn.fetch(
                            "SELECT content, step_number, metadata, created_at FROM reasoning_traces WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3 ORDER BY created_at ASC",
                            t_id, u_id, s_id
                        )
                        payload = {
                            "event": "PRE_PURGE_ARCHIVE",
                            "tenant_id": str(t_id),
                            "user_id": u_id,
                            "session_id": s_id,
                            "data_type": "reasoning",
                            "traces": [dict(r) for r in traces]
                        }
                        # Convert datetime to string for JSON serialization
                        for t in payload["traces"]:
                            t["created_at"] = t["created_at"].isoformat()
                            if isinstance(t["metadata"], str):
                                t["metadata"] = json.loads(t["metadata"])

                        async with httpx.AsyncClient() as client:
                            resp = await client.post(webhook_url, json=payload, timeout=30.0)
                            if resp.status_code >= 300:
                                logger.error(f"Reasoning Retention Webhook Failed ({resp.status_code}). Skipping purge.")
                                continue
                    except Exception as e:
                        logger.error(f"Reasoning Retention Webhook Error: {e}")
                        continue

                # 3. Purge
                await conn.execute(
                    "DELETE FROM reasoning_traces WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3 AND created_at < NOW() - make_interval(days := $4)",
                    t_id, u_id, s_id, retention_days
                )
                logger.info(f"Retention Engine: Purged reasoning traces for session {s_id}.")

        return True

class ReasoningExtractor:
    """
    Robust state-machine for extracting and filtering internal reasoning/planning tags from LLM streams.
    Handles split tags across network chunks and supports multiple tag pairs.
    """

    def __init__(self, tags_to_strip: Optional[List[str]] = None):
        self.tags_to_strip = tags_to_strip or ["thought", "think", "ice_plan"]
        self.buffer_state = 0  # 0 = Forwarding, 1 = Buffering
        self.current_tag = ""
        self.current_buffer = ""
        self.tag_detect_buffer = ""
        self.lookahead_size = 20  # Increased for longer tags like </ice_plan>

    def process_chunk(self, delta: str) -> tuple[str, list[tuple[str, str]]]:
        """
        Processes a chunk and returns (clean_text, list_of_extracted_tag_content).
        The list of extracted content is a list of (tag_name, content).
        """
        self.tag_detect_buffer += delta
        output_text = ""
        extracted = []

        while len(self.tag_detect_buffer) > 0:
            if self.buffer_state == 0:  # Forwarding
                # If buffer is too small to definitively say 'no tag', and we don't see one yet, wait
                if len(self.tag_detect_buffer) < self.lookahead_size:
                    could_be_tag = False
                    for tag in self.tags_to_strip:
                         if f"<{tag}>".startswith(self.tag_detect_buffer) or f"[{tag}]".startswith(self.tag_detect_buffer):
                             could_be_tag = True
                             break
                    if could_be_tag:
                         break # Need more data to be sure

                found_tag = None
                prefix_len = 0
                for tag in self.tags_to_strip:
                    if self.tag_detect_buffer.startswith(f"<{tag}>"):
                        found_tag = tag
                        prefix_len = len(tag) + 2
                    elif self.tag_detect_buffer.startswith(f"[{tag}]"):
                        found_tag = tag
                        prefix_len = len(tag) + 2
                    
                    if found_tag: break
                
                if found_tag:
                    self.buffer_state = 1
                    self.current_tag = found_tag
                    self.current_buffer = ""
                    self.tag_detect_buffer = self.tag_detect_buffer[prefix_len:]
                else:
                    output_text += self.tag_detect_buffer[0]
                    self.tag_detect_buffer = self.tag_detect_buffer[1:]
            else:  # Buffering
                actual_suffix = ""
                if self.tag_detect_buffer.startswith(f"</{self.current_tag}>"):
                    actual_suffix = f"</{self.current_tag}>"
                elif self.tag_detect_buffer.startswith(f"[/{self.current_tag}]"):
                    actual_suffix = f"[/{self.current_tag}]"
                
                if actual_suffix:
                    self.buffer_state = 0
                    extracted.append((self.current_tag, self.current_buffer.strip()))
                    self.tag_detect_buffer = self.tag_detect_buffer[len(actual_suffix):]
                    self.current_tag = ""
                    self.current_buffer = ""
                else:
                    # If buffer is too small to see a potential closer, wait
                    if len(self.tag_detect_buffer) < (len(self.current_tag) + 4):
                         break
                    self.current_buffer += self.tag_detect_buffer[0]
                    self.tag_detect_buffer = self.tag_detect_buffer[1:]

        return output_text, extracted

    def flush(self) -> tuple[str, list[tuple[str, str]]]:
        """
        Flushes any remaining content in the buffers at the end of the stream.
        """
        remaining = self.tag_detect_buffer
        self.tag_detect_buffer = ""
        
        output_text = ""
        extracted = []
        
        if self.buffer_state == 0:
            output_text = remaining
        else:
            # If we were buffering a tag, we expose it as "unfinished"
            unfinished = self.current_buffer + remaining
            if unfinished.strip():
                extracted.append((self.current_tag, unfinished.strip()))
            self.current_buffer = ""
            self.buffer_state = 0
            
        return output_text, extracted

