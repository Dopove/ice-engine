class MemoryStore:
    """Base interface for ICE persistence."""
    def __init__(self, connection_string=None):
        self.connection_string = connection_string
    
    async def retrieve(self, query: str):
        # Placeholder for DuckDB/Postgres retrieval
        return []
        
    async def save(self, role: str, content: str):
        # Placeholder for persistence
        pass
