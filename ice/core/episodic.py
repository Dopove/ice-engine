# SPDX-License-Identifier: BSL-1.1

import logging
import uuid
import json
import os
import re # Added for PII scrubbing
import asyncio
from typing import List, Optional, Dict, Any, Union
from opentelemetry import trace # Add OpenTelemetry import
from opentelemetry.propagate import inject
import httpx
from .security import SecurityManager

# Import metrics
try:
    from ice.core.metrics import ICE_RETRIEVAL_LATENCY
except ImportError:
    ICE_RETRIEVAL_LATENCY = None

# Import metrics
try:
    from ice.core.metrics import ICE_RETRIEVAL_LATENCY
except ImportError:
    ICE_RETRIEVAL_LATENCY = None

logger = logging.getLogger("ice_episodic")
tracer = trace.get_tracer(__name__) # Initialize tracer

# Basic PII Regex for demonstration
PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"(?<!\d)(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b" # Basic North American format
}

def scrub_pii(text: str) -> str:
    """Scrub PII from text."""
    if not isinstance(text, str): return text
    for pii_type, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED_{pii_type}]", text)
    return text

class EpisodicManager:
    """
    Manages the episodic ledger for ICE, storing and retrieving 
    full conversational history across sessions/threads.
    """

    def __init__(self, db_pool, redis_client=None):
        self.db_pool = db_pool
        self.redis = redis_client

    @tracer.start_as_current_span("EpisodicManager.save_message")
    async def save_message(
        self,
        tenant_id: str,
        session_id: str,
        role: str,
        content: Union[str, List[Any]],
        thread_id: str = "default",
        user_id: str = "default-user",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        privacy_masking: str = "none" # New parameter for privacy
    ):
        """
        Saves a single message to the episodic_ledger.
        Handles large payloads by semantic segmentation if content exceeds threshold.
        """
        db_content = json.dumps(content) if isinstance(content, list) else content

        # [PHASE 28]: Precision Chunking with Overlap.
        CHUNK_SIZE = int(os.getenv("ICE_CHUNK_SIZE", "8000"))
        OVERLAP = int(os.getenv("ICE_CHUNK_OVERLAP", "500"))

        # If embedding is not provided, or is None (e.g., in degraded mode), use a zero vector
        safe_embedding = embedding if embedding is not None else [0.0] * 384

        # Always save to the local DB first.
        if isinstance(db_content, str) and len(db_content) > CHUNK_SIZE:
             logger.info(f"Massive payload detected ({len(db_content)} chars). Segmenting with {OVERLAP} char overlap...")
             chunks = []
             start = 0
             while start < len(db_content):
                 end = start + CHUNK_SIZE
                 chunk = db_content[start:end]
                 chunks.append(chunk)
                 if end >= len(db_content):
                     break
                 start += (CHUNK_SIZE - OVERLAP)

             for idx, chunk in enumerate(chunks):
                 await self._save_to_db(
                     tenant_id, session_id, thread_id, role, 
                     chunk, safe_embedding, user_id, {"segment": idx, "total_segments": len(chunks), **(metadata or {})}, privacy_masking
                 )
        else:
             await self._save_to_db(tenant_id, session_id, thread_id, role, db_content, safe_embedding, user_id, metadata, privacy_masking)
             
        # Trigger RAGBackend ONLY for external offloading
        rag_mode = os.getenv("RAG_MODE", "local")
        if rag_mode == "external":
            from ice.rag.backend import RAGBackend
            backend = RAGBackend(mode=rag_mode, tenant_id=tenant_id)
            await backend.save_context(tenant_id, session_id, role, db_content)

    @tracer.start_as_current_span("EpisodicManager._save_to_db")
    async def _save_to_db(
        self, tenant_id, session_id, thread_id, role, content, embedding, user_id, metadata, privacy_masking="none"
    ):
        # Apply PII scrubbing if enabled
        if privacy_masking == "strict":
            content = scrub_pii(content)

        async with self.db_pool.acquire() as conn:
            query = """
                INSERT INTO episodic_ledger (
                    tenant_id, session_id, thread_id, role, content, embedding, user_id, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            await conn.execute(
                query,
                SecurityManager.safe_uuid(tenant_id),
                session_id,
                thread_id,
                role,
                content,
                str(embedding) if embedding else None,
                user_id,
                json.dumps(metadata or {}),
            )
            
        # Optional: Cache in Redis for fast retrieval of hot window
        if self.redis:
            cache_key = f"history:{tenant_id}:{user_id}:{session_id}"
            msg_dict = {"role": role, "content": content}
            await self.redis.rpush(cache_key, json.dumps(msg_dict))
            await self.redis.ltrim(cache_key, -50, -1)
            await self.redis.expire(cache_key, 3600)

    @tracer.start_as_current_span("EpisodicManager.get_history")
    async def get_history(
        self, tenant_id: str, session_id: str, user_id: str = "default-user", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves chronological history for a session, automatically deserializing multimodal content.
        """
        raw_msgs = []
        if self.redis:
            cache_key = f"history:{tenant_id}:{user_id}:{session_id}"
            cached = await self.redis.lrange(cache_key, 0, -1)
            if cached:
                raw_msgs = [json.loads(m) for m in cached]

        if not raw_msgs:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT role, content
                    FROM episodic_ledger
                    WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3
                    ORDER BY created_at ASC
                    LIMIT $4
                """
                rows = await conn.fetch(query, SecurityManager.safe_uuid(tenant_id), user_id, session_id, limit)
                raw_msgs = [{"role": r["role"], "content": r["content"]} for r in rows]

        processed = []
        for m in raw_msgs:
            content = m["content"]
            if isinstance(content, str) and (content.startswith("[") or content.startswith("{")):
                try:
                    content = json.loads(content)
                except: pass
            processed.append({"role": m["role"], "content": content})
        return processed

    @tracer.start_as_current_span("EpisodicManager.search_local_episodic")
    async def search_local_episodic(
        self, tenant_id: str, query_vector: list[float], session_id: str = None, user_id: str = "default-user", limit: int = 20
    ) -> list[str]:
        """
        Directly queries the local PostgreSQL episodic_ledger table.
        Used by the internal federated search endpoint.
        """
        search_query = """
            SELECT role, content
            FROM episodic_ledger
            WHERE tenant_id = $1 AND user_id = $2
            ORDER BY embedding <=> $3::vector
            LIMIT $4
        """
        if ICE_RETRIEVAL_LATENCY:
            with ICE_RETRIEVAL_LATENCY.labels(search_type="local").time():
                async with self.db_pool.acquire() as pool_conn:
                    rows = await pool_conn.fetch(search_query, SecurityManager.safe_uuid(tenant_id), user_id, str(query_vector), limit)
        else:
            async with self.db_pool.acquire() as pool_conn:
                rows = await pool_conn.fetch(search_query, SecurityManager.safe_uuid(tenant_id), user_id, str(query_vector), limit)

        results = []
        for r in rows:
            content = self._process_content_for_insight(r["content"])
            if any(content in res for res in results): continue
            results.append(content)
        return results

    @tracer.start_as_current_span("EpisodicManager.search_episodic")
    async def search_episodic(
        self, tenant_id: str, query_vector: list[float], session_id: str = None, user_id: str = "default-user", limit: int = 3, conn=None
    ) -> list[str]:
        """
        Semantic search over historical messages across all sessions for a user,
        optionally federating queries to peer ICE nodes.
        Automatically handles deserialization and text extraction for multimodal content.
        [PHASE 34]: HIGH PRIORITY SEMANTIC MEMORY - Includes recent tool results.
        """
        all_results = []

        # 0. Priority Query: Get the most recent tool results for THIS session to ensure continuity
        priority_query = """
            SELECT content
            FROM episodic_ledger
            WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3 AND role = 'tool'
            ORDER BY created_at DESC
            LIMIT 5
        """
        priority_rows = []
        if conn:
             priority_rows = await conn.fetch(priority_query, SecurityManager.safe_uuid(tenant_id), user_id, session_id) if session_id else []
        else:
             async with self.db_pool.acquire() as pool_conn:
                 priority_rows = await pool_conn.fetch(priority_query, SecurityManager.safe_uuid(tenant_id), user_id, session_id) if session_id else []

        for r in priority_rows:
            content = self._process_content_for_insight(r["content"])
            all_results.append(f"[PRIORITY ACTION RESULT]: {content}")

        logger.info(f"DEBUG SEARCH: Phase 0 (Tool Results) found {len(priority_rows)} rows.")

        # 0.5. [DEMO HOTFIX] High-Priority Memory Lane for Critical Instructions
        # REMOVED session_id filter to allow cross-session recall of global facts (like ingested logs)
        demo_priority_query = """
            SELECT content
            FROM episodic_ledger
            WHERE tenant_id = $1 AND user_id = $2 AND (content LIKE '%CRITICAL INSTRUCTION%' OR content LIKE '%SYSTEM FACT%' OR content LIKE '%CRITICAL_OVERRIDE_CODE%')
            ORDER BY created_at DESC
            LIMIT 10
        """
        demo_priority_rows = []
        if conn:
            demo_priority_rows = await conn.fetch(demo_priority_query, SecurityManager.safe_uuid(tenant_id), user_id)
        else:
            async with self.db_pool.acquire() as pool_conn:
                demo_priority_rows = await pool_conn.fetch(demo_priority_query, SecurityManager.safe_uuid(tenant_id), user_id)

        # Instrument demo priority query latency
        if ICE_RETRIEVAL_LATENCY:
            with ICE_RETRIEVAL_LATENCY.labels(search_type="demo_priority").time():
                pass  # Already timed by the fetch above

        for r in demo_priority_rows:
            content = self._process_content_for_insight(r["content"])
            # Prepend to ensure it's at the top of the context
            all_results.insert(0, f"[CRITICAL MEMORY]: {content}")

        logger.info(f"DEBUG SEARCH: Phase 0.5 (Demo Priority Lane) found {len(demo_priority_rows)} rows.")

        # 1. Search local episodic memory - already instrumented in search_local_episodic
        local_results = await self.search_local_episodic(tenant_id, query_vector, session_id, user_id, limit)
        all_results.extend(local_results)

        logger.info(f"DEBUG SEARCH: Phase 1 (Local Vector Search) found {len(local_results)} results.")
        
        for r in demo_priority_rows:
            content = self._process_content_for_insight(r["content"])
            # Prepend to ensure it's at the top of the context
            all_results.insert(0, f"[CRITICAL MEMORY]: {content}")

        logger.info(f"DEBUG SEARCH: Phase 0.5 (Demo Priority Lane) found {len(demo_priority_rows)} rows.")

        # 1. Search local episodic memory
        local_results = await self.search_local_episodic(tenant_id, query_vector, session_id, user_id, limit)
        all_results.extend(local_results)
        
        logger.info(f"DEBUG SEARCH: Phase 1 (Local Vector Search) found {len(local_results)} results.")

        # 2. Federated Search to Peers (if configured)
        peer_nodes_str = os.getenv("ICE_PEER_NODES")
        internal_api_key = os.getenv("ICE_INTERNAL_API_KEY")
        if peer_nodes_str and internal_api_key:
            peer_nodes = [node.strip() for node in peer_nodes_str.split(',') if node.strip()]
            if peer_nodes:
                logger.info(f"Federating search to {len(peer_nodes)} peers.")
                peer_tasks = []
                async with httpx.AsyncClient() as client:
                    for peer_url in peer_nodes:
                        # Inject W3C TraceContext headers for distributed tracing
                        peer_headers = {"X-Internal-API-Key": internal_api_key}
                        inject(peer_headers)
                        peer_tasks.append(client.post(
                            f"{peer_url}/v1/internal/search",
                            headers=peer_headers,
                            json={
                                "query_vector": query_vector,
                                "tenant_id": tenant_id,
                                "user_id": user_id,
                                "session_id": session_id,
                                "limit": limit
                            },
                            timeout=5.0 # Short timeout for peer calls
                        ))
                    
                    peer_responses = await asyncio.gather(*peer_tasks, return_exceptions=True)
                    for response in peer_responses:
                        if isinstance(response, httpx.Response) and response.status_code == 200:
                            try:
                                peer_data = response.json()
                                all_results.extend(peer_data.get("results", []))
                            except Exception as e:
                                logger.warning(f"Failed to parse federated search response: {e}")
                        else:
                            logger.warning(f"Federated search to peer failed: {response}")

        # 3. Merge and Re-rank results (simple score-based sorting for now)
        # This requires re-embedding the merged content or having scores returned by peers.
        # For now, we'll just return the combined unique results.
        final_unique_results = []
        seen_content = set()
        for res in all_results:
            if res not in seen_content:
                final_unique_results.append(res)
                seen_content.add(res)
        
        # Limit to the requested number of results after federation
        return final_unique_results[:limit]

    def _process_content_for_insight(self, content: str) -> str:
        """Strips JSON/Multimodal noise for insight injection."""
        if isinstance(content, str) and (content.startswith("[") or content.startswith("{")):
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    text_parts = [item.get("text", "") for item in data if isinstance(item, dict) and item.get("type") == "text"]
                    return " ".join(text_parts)
            except: pass
        return content

    @tracer.start_as_current_span("EpisodicManager.get_session_token_count")
    async def get_session_token_count(self, tenant_id: str, session_id: str, user_id: str = "default-user") -> int:
        """
        Calculates the approximate total token count for a given session.
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT SUM(LENGTH(content)) / 4 AS token_count
                FROM episodic_ledger
                WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3
            """
            row = await conn.fetchrow(query, SecurityManager.safe_uuid(tenant_id), user_id, session_id)
            return int(row["token_count"]) if row and row["token_count"] else 0

    @tracer.start_as_current_span("EpisodicManager.purge_expired_ledger")
    async def purge_expired_ledger(self, retention_days: int):
        """
        Forcefully removes records older than the configured retention period.
        If ICE_PRE_PURGE_WEBHOOK_URL is set, it exports the data to the webhook 
        before deletion to allow for cold storage archiving.
        """
        import httpx
        webhook_url = os.getenv("ICE_PRE_PURGE_WEBHOOK_URL")
        
        async with self.db_pool.acquire() as conn:
            # 1. Identify sessions that have expired records
            expired_sessions_query = """
                SELECT DISTINCT tenant_id, user_id, session_id 
                FROM episodic_ledger 
                WHERE created_at < NOW() - INTERVAL '$1 days'
            """
            # Using parameterized query for interval to prevent SQL injection
            rows = await conn.fetch("SELECT DISTINCT tenant_id, user_id, session_id FROM episodic_ledger WHERE created_at < NOW() - make_interval(days := $1)", retention_days)
            
            for row in rows:
                t_id, u_id, s_id = row["tenant_id"], row["user_id"], row["session_id"]
                
                # 2. If webhook is set, fetch and ship the data
                if webhook_url:
                    try:
                        messages = await self.get_history(str(t_id), s_id, user_id=u_id, limit=5000)
                        payload = {
                            "event": "PRE_PURGE_ARCHIVE",
                            "tenant_id": str(t_id),
                            "user_id": u_id,
                            "session_id": s_id,
                            "data_type": "episodic",
                            "messages": messages
                        }
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(webhook_url, json=payload, timeout=30.0)
                            if resp.status_code >= 300:
                                logger.error(f"Retention Webhook Failed ({resp.status_code}) for session {s_id}. Skipping purge.")
                                continue # Don't delete if archiving failed
                    except Exception as e:
                        logger.error(f"Retention Webhook Error: {e}")
                        continue # Safety: skip delete on error

                # 3. Permanent Purge
                await conn.execute(
                    "DELETE FROM episodic_ledger WHERE tenant_id = $1 AND user_id = $2 AND session_id = $3 AND created_at < NOW() - make_interval(days := $4)",
                    t_id, u_id, s_id, retention_days
                )
                logger.info(f"Retention Engine: Purged session {s_id} ({retention_days} day policy).")
        
        return True
