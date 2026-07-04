import os
import json
import asyncio
from datetime import datetime

class MemoryStore:
    """
    DuckDB-based local-first memory store for ICE.
    If no connection string is provided, it defaults to a local file.
    """
    def __init__(self, connection_string=None):
        self.db_path = connection_string or "ice_memory.db"
        self._initialized = False
        self._con = None

    async def _init_db(self):
        if self._initialized:
            return
        
        # We lazy-load duckdb to keep dependencies light
        try:
            import duckdb
        except ImportError:
            # Fallback for minimal installs
            print("Warning: duckdb not installed. Local memory will be volatile.")
            self._con = None
            self._initialized = True
            return

        self._con = duckdb.connect(self.db_path)
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role VARCHAR,
                content TEXT,
                metadata JSON
            )
        """)
        self._initialized = True

    async def retrieve(self, query: str, limit: int = 5):
        await self._init_db()
        if not self._con:
            return []

        # For the basic OSS version, we use a simple keyword search 
        # as a fallback if vector extensions aren't loaded.
        # This ensures 'Zero-Conf' works on any machine.
        try:
            res = self._con.execute(
                "SELECT content FROM episodic_memory WHERE content ILIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            return [r[0] for r in res]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    async def save(self, role: str, content: str, metadata: dict = None):
        await self._init_db()
        if not self._con:
            return

        metadata_json = json.dumps(metadata or {})
        try:
            self._con.execute(
                "INSERT INTO episodic_memory (role, content, metadata) VALUES (?, ?, ?)",
                (role, content, metadata_json)
            )
        except Exception as e:
            print(f"Save error: {e}")
