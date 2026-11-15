# SPDX-License-Identifier: BSL-1.1

from prometheus_client import Counter, Histogram, Gauge

# =============================================================================
# Core Query Metrics
# =============================================================================
ICE_TOTAL_QUERIES = Counter('ice_total_queries', 'Total number of queries handled by ICE')
ICE_EMBEDDING_CACHE_HITS = Counter('ice_embedding_cache_hits', 'Number of embedding cache hits')
ICE_EMBEDDING_CACHE_MISSES = Counter('ice_embedding_cache_misses', 'Number of embedding cache misses')
ICE_GENERATION_LATENCY = Histogram('ice_generation_latency_seconds', 'Latency of ICE chunk generation')

# =============================================================================
# Database Connection Pool Metrics
# =============================================================================
ICE_DB_POOL_ACQUIRED = Gauge('ice_db_pool_acquired_connections', 'Number of acquired PostgreSQL connections')
ICE_DB_POOL_AVAILABLE = Gauge('ice_db_pool_available_connections', 'Number of available PostgreSQL connections')

# =============================================================================
# Session & Tenant Metrics
# =============================================================================
ICE_ACTIVE_SESSIONS = Gauge(
    'ice_active_sessions',
    'Current active sessions per tenant',
    ['tenant_id']
)
ICE_TENANT_QUOTA_USAGE = Gauge(
    'ice_tenant_quota_usage',
    'Token/quota usage vs license limits',
    ['tenant_id', 'limit_type']  # limit_type: tokens_per_session, concurrent_sessions, max_tenants
)

# =============================================================================
# Upstream LLM Provider Metrics
# =============================================================================
ICE_UPSTREAM_LATENCY = Histogram(
    'ice_upstream_latency_seconds',
    'Latency per upstream LLM provider',
    ['provider', 'model'],  # provider: openai, anthropic, gemini, ollama
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)
ICE_UPSTREAM_ERRORS = Counter(
    'ice_upstream_errors_total',
    'Upstream LLM errors by provider and error type',
    ['provider', 'error_type']  # error_type: timeout, rate_limit, auth, server_error, network
)

# =============================================================================
# Circuit Breaker Metrics
# =============================================================================
ICE_CIRCUIT_BREAKER_STATE = Gauge(
    'ice_circuit_breaker_state',
    'Circuit breaker state: 0=closed, 1=open, 2=half_open',
    ['provider']  # provider: openai, anthropic, gemini, ollama
)

# =============================================================================
# Memory & Storage Metrics
# =============================================================================
ICE_MEMORY_USAGE = Gauge(
    'ice_memory_usage_bytes',
    'Current memory usage for episodic and reasoning storage',
    ['storage_type']  # episodic, reasoning, total
)

# =============================================================================
# Retrieval & Chunk Generation Metrics
# =============================================================================
ICE_CHUNK_GENERATION_DURATION = Histogram(
    'ice_chunk_generation_duration_seconds',
    'Per-chunk generation latency',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
ICE_RETRIEVAL_LATENCY = Histogram(
    'ice_retrieval_latency_seconds',
    'Episodic/reasoning search latency',
    ['search_type'],  # local, remote, hybrid
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

# =============================================================================
# System Health Metrics
# =============================================================================
ICE_DEGRADED_MODE = Gauge(
    'ice_degraded_mode',
    '1 if ICE is in degraded mode (DB/Redis unavailable), 0 if healthy'
)
ICE_LICENSE_TIER = Gauge(
    'ice_license_tier',
    'License tier enum: 1=community, 2=developer_pro, 3=enterprise',
    ['sku']
)

# =============================================================================
# Token Usage Metrics (for billing/monitoring)
# =============================================================================
ICE_TOKENS_INPUT = Counter(
    'ice_tokens_input_total',
    'Cumulative input tokens sent to upstream LLMs',
    ['tenant_id', 'provider']
)
ICE_TOKENS_OUTPUT = Counter(
    'ice_tokens_output_total',
    'Cumulative output tokens received from upstream LLMs',
    ['tenant_id', 'provider']
)

# =============================================================================
# Cache Efficiency Metrics
# =============================================================================
ICE_CACHE_HIT_RATIO = Gauge(
    'ice_cache_hit_ratio',
    'Redis hot-cache efficiency (hits / (hits + misses))',
    ['cache_type']  # embedding, reasoning, episodic
)

# =============================================================================
# Resource Usage Metrics
# =============================================================================
ICE_RESOURCE_USAGE = Gauge(
    'ice_resource_usage_bytes',
    'VMM RAM footprint and resource consumption',
    ['resource_type']  # rss, vms, voxel_registry
)

# =============================================================================
# Concurrency Metrics
# =============================================================================
ICE_STITCH_SEMAPHORE_LOCKED = Gauge(
    'ice_stitch_semaphore_locked',
    'Active recursive synthesis tasks (stitch operations)'
)