import os
import asyncio
from typing import Optional
from ice.sdk import init, InfiniteContextClient

# --- Global ICE Client Instance ---
_global_ice_client: Optional[InfiniteContextClient] = None

def get_ice_client() -> InfiniteContextClient:
    """
    Dependency injection provider for FastAPI.
    Ensures the ICE client is initialized and returns the singleton instance.
    """
    if _global_ice_client is None:
        raise RuntimeError("ICE Kernel not initialized. Ensure initialize_ice_kernel() is called at startup.")
    return _global_ice_client

async def initialize_ice_kernel():
    """
    Initializes the global ICE Kernel instance during application startup.
    This function consolidates all enterprise-grade customization via environment variables.
    """
    global _global_ice_client
    if _global_ice_client is not None:
        print("[ICE Config]: Kernel already initialized. Skipping.")
        return

    print("[ICE Config]: Initializing Enterprise ICE Kernel with Customizations...")

    # --- 1. License & Basic Setup ---
    # Your cryptographic license JWT provided by Dopove. Absolutely critical for production.
    # In development, can often be bypassed with a 'arn:aws:license-manager::050752616731:license:l-cfb0b93faa3b40ce80294235bfa79425' or similar if ICE_ALLOW_DEFAULT_KEY=1.
    license_key = os.getenv("ICE_LICENSE_JWT")
    if not license_key:
        print("[ICE Config]: WARNING: ICE_LICENSE_JWT not set. Running in DEVELOPMENT mode (may have limited features).", file=sys.stderr)
        # Fallback to dev key if allowed for local testing
        if os.getenv("ICE_ALLOW_DEFAULT_KEY", "0") == "1":
            license_key = "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"        else:
            raise ValueError("ICE_LICENSE_JWT is required for production deployments.")

    # --- 2. Scaling & Resource Management (docs/installation/CONFIGURATION.md) ---
    # Target memory threshold for context operations. Align with Kubernetes/Docker container limits.
    memory_cap_gb = float(os.getenv("ICE_MEMORY_CAP_GB", "16.0"))
    # Max concurrent long-context operations per node. Prevents KV-cache thrashing.
    max_stitch_concurrency = int(os.getenv("ICE_MAX_STITCH_CONCURRENCY", "20"))
    # Number of parallel Uvicorn worker processes (should align with CPU cores).
    ice_workers = int(os.getenv("ICE_WORKERS", "4"))
    # Min/Max PostgreSQL connection pool size.
    db_min_pool = int(os.getenv("ICE_DB_MIN_POOL", "5"))
    db_max_pool = int(os.getenv("ICE_DB_MAX_POOL", "20"))

    # --- 3. Context & Precision Paging Orchestration ---
    # Total virtual context budget (input + output) for the underlying LLM.
    max_tokens = int(os.getenv("ICE_MODEL_CONTEXT_WINDOW", "32768"))
    # Max context size fed to LLM (ICE will auto-page from the 100B horizon).
    max_input_tokens = int(os.getenv("ICE_POST_COMPRESSION_LIMIT", "24000")) 
    # Default token generation budget if client doesn't specify.
    default_output_tokens = int(os.getenv("ICE_DEFAULT_OUTPUT_TOKENS", "1024"))
    # Max recursive turns for the "Turbo-Stitching" output engine.
    max_continuations = int(os.getenv("ICE_MAX_CONTINUATIONS", "10"))
    # Toggles intelligent intent-based token budgeting.
    enable_smart_sizing = os.getenv("ICE_DYNAMIC_OUTPUT_BUDGET", "true").lower() == "true"
    # Target chunk size (characters) for document semantic partitioning.
    chunk_size = int(os.getenv("ICE_CHUNK_SIZE", "8000"))
    # Overlap (characters) between chunks to prevent data loss.
    chunk_overlap = int(os.getenv("ICE_CHUNK_OVERLAP", "500"))

    # --- 4. Compliance & Retention (Data Governance) ---
    # Days data is retained before automated purging (GDPR compliance).
    retention_days = int(os.getenv("ICE_RETENTION_DAYS", "90"))
    # Webhook to POST data to before purging (for cold-storage/archiving).
    pre_purge_webhook_url = os.getenv("ICE_PRE_PURGE_WEBHOOK_URL")
    # Enables PII redaction and compliance scrubbing on ingested documents.
    rag_enable_compliance = os.getenv("ICE_RAG_ENABLE_COMPLIANCE", "false").lower() == "true"
    # Aggressiveness of PII redaction (standard, strict, paranoid).
    rag_compliance_level = os.getenv("ICE_RAG_COMPLIANCE_LEVEL", "standard")

    # --- 5. Multimodal Pipeline ---
    # Document parsing engine (e.g., "docling" for high-fidelity, "local" for fast local text).
    rag_parser = os.getenv("ICE_RAG_PARSER", "docling")
    # Process images and diagrams from uploaded documents.
    enable_images = os.getenv("ICE_RAG_ENABLE_IMAGES", "true").lower() == "true"
    # Extract and process tables from documents.
    enable_tables = os.getenv("ICE_RAG_ENABLE_TABLES", "true").lower() == "true"
    # Extract and process LaTeX/mathematical equations.
    enable_equations = os.getenv("ICE_RAG_ENABLE_EQUATIONS", "true").lower() == "true"
    # Sandboxed directory for RAG file ingestion.
    upload_dir = os.getenv("ICE_UPLOAD_DIR", "./uploads")

    # --- 6. Security & Telemetry ---
    # Cryptographic secret for signing offline JWT licenses and hardware seals.
    secret_key = os.getenv("ICE_SECRET_KEY", "default-dev-secret-key-12345")
    # Enables/disables OpenTelemetry tracing.
    telemetry_enabled = os.getenv("ICE_TELEMETRY_ENABLED", "true").lower() == "true"
    # OTLP endpoint for trace export (e.g., to Jaeger/Datadog).
    otel_exporter_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    # --- 7. Upstream LLM Routing ---
    # Base URL for the upstream LLM proxy (e.g., local Ollama, or a custom service).
    upstream_api_url = os.getenv("UPSTREAM_API_URL", "http://localhost:11434/v1/chat/completions")
    # Specific routing target for OpenAI models.
    openai_api_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    # Specific routing target for Anthropic models.
    anthropic_api_url = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    # --- 8. Infrastructure Connections ---
    # PostgreSQL connection string for the Semantic Ledger.
    database_url = os.getenv("DATABASE_URL", "postgres://ice_user:ice_password@localhost:5432/ice_db")
    # Redis connection string for the Hot Window Cache.
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- Initialize the ICE Kernel with all configured options ---
    _global_ice_client = await init(
        license_key=license_key,
        max_input_tokens=max_input_tokens,
        max_tokens=max_tokens,
        default_output_tokens=default_output_tokens,
        max_continuations=max_continuations,
        enable_smart_sizing=enable_smart_sizing,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        retention_days=retention_days,
        pre_purge_webhook_url=pre_purge_webhook_url,
        rag_enable_compliance=rag_enable_compliance,
        rag_compliance_level=rag_compliance_level,
        rag_parser=rag_parser,
        enable_images=enable_images,
        enable_tables=enable_tables,
        enable_equations=enable_equations,
        upload_dir=upload_dir,
        secret_key=secret_key,
        telemetry_enabled=telemetry_enabled,
        otel_exporter_endpoint=otel_exporter_endpoint,
        upstream_api_url=upstream_api_url,
        openai_api_url=openai_api_url,
        openai_api_key=openai_api_key,
        anthropic_api_url=anthropic_api_url,
        anthropic_api_key=anthropic_api_key,
        database_url=database_url,
        redis_url=redis_url,
        db_min_pool=db_min_pool,
        db_max_pool=db_max_pool,
        # Note: ICE_MEMORY_CAP_GB, ICE_MAX_STITCH_CONCURRENCY are managed
        # internally by the kernel based on these parameters.
    )
    print("[ICE Config]: Enterprise ICE Kernel READY with custom configuration.")
