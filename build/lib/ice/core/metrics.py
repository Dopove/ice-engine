from prometheus_client import Counter, Histogram, Gauge

ICE_TOTAL_QUERIES = Counter('ice_total_queries', 'Total number of queries handled by ICE')
ICE_EMBEDDING_CACHE_HITS = Counter('ice_embedding_cache_hits', 'Number of embedding cache hits')
ICE_EMBEDDING_CACHE_MISSES = Counter('ice_embedding_cache_misses', 'Number of embedding cache misses')
ICE_GENERATION_LATENCY = Histogram('ice_generation_latency_seconds', 'Latency of ICE chunk generation')
ICE_DB_POOL_ACQUIRED = Gauge('ice_db_pool_acquired_connections', 'Number of acquired PostgreSQL connections')
ICE_DB_POOL_AVAILABLE = Gauge('ice_db_pool_available_connections', 'Number of available PostgreSQL connections')