# SPDX-License-Identifier: MIT

import duckdb
import os
import uuid

class MemoryStore:
    def __init__(self, connection_string=None):
        self.db_path = connection_string or os.path.expanduser("~/.ice/ice_memory.db")
        self._initialized = False

    async def _init_db(self):
        if self._initialized:
            return
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
        try:
            with duckdb.connect(self.db_path) as con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS episodic_memory (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        role VARCHAR,
                        content TEXT,
                        metadata JSON
                    )
                """)
            self._initialized = True
        except ImportError:
            print("Warning: duckdb not installed. Local memory will be volatile.")
            self._initialized = True

    async def save(self, role, content, metadata=None):
        await self._init_db()
        with duckdb.connect(self.db_path) as con:
            con.execute("INSERT INTO episodic_memory (role, content, metadata) VALUES (?, ?, ?)", 
                        (role, content, str(metadata) if metadata else None))

    async def retrieve(self, query):
        await self._init_db()
        with duckdb.connect(self.db_path) as con:
            results = con.execute("SELECT content FROM episodic_memory ORDER BY timestamp DESC LIMIT 5").fetchall()
            return [r[0] for r in results]
