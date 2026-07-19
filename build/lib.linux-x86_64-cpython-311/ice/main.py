from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Header,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal, Annotated
import logging
import httpx
import time
import os
import asyncio
import ctypes # Added import
import asyncpg
import redis.asyncio as redis
import orjson
import hashlib
import re
import sys
import psutil
import boto3
import uuid
import uuid
from contextlib import asynccontextmanager

from .core.rcc_ffi.wrapper import get_lib, IceMessage, IceVector, IceStringArray, AssembledPrompt, rcc_free_string_array, rcc_free_assembled_prompt

class InternalSearchRequest(BaseModel):
    query_vector: List[float]
    tenant_id: str
    user_id: str
    session_id: str
    limit: int = Field(default=5, ge=1, le=20)

async def verify_internal_api_key(x_internal_api_key: str = Header(...)):
    if x_internal_api_key != os.getenv("ICE_INTERNAL_API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Internal API Key.")

from .core.pager import ContextPager, EmbeddingModel

async def get_secret_from_aws_secrets_manager(secret_name: str, region_name: str = "us-east-1") -> Optional[str]:
    """
    Retrieves a secret from AWS Secrets Manager using a thread pool to avoid blocking the event loop.
    """
    # Validate secret name to prevent path traversal or malicious injection
    if not re.match(r"^[a-zA-Z0-9/_+=.@-]+$", secret_name):
        logger.error(f"INVALID SECRET NAME: {secret_name}")
        return None

    def _get_secret():
        client = boto3.client("secretsmanager", region_name=region_name)
        return client.get_secret_value(SecretId=secret_name)

    try:
        # Offload blocking boto3 call to a separate thread
        response = await asyncio.to_thread(_get_secret)
        if "SecretString" in response:
            return response["SecretString"]
        return None
    except Exception as e:
        logging.warning(f"AWS Secrets Manager lookup failed for '{secret_name}': {e}")
        return None

from .core.reasoning import ReasoningManager, ReasoningExtractor
from .core.episodic import EpisodicManager
from .core.ingestion import IngestionPipeline
from .core.security import enforce_licensing
from .core.providers import get_provider_adapter
from prometheus_fastapi_instrumentator import Instrumentator
from .core.billing import meter_usage # Added import

# --- OpenTelemetry Configuration ---
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import StatusCode

resource = Resource.create({"service.name": "ice-engine", "service.version": "3.0.0"})
provider = TracerProvider(resource=resource)

class ErrorOnlySpanProcessor(BatchSpanProcessor):
    """
    Tail-based sampling at the network edge.
    Only transmits telemetry spans to the global AWS receiver if a critical error occurs.
    This reduces outbound network I/O by >99% and ensures zero-latency impact during healthy load.
    """
    def on_end(self, span):
        if span.status.status_code == StatusCode.ERROR:
            super().on_end(span)

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    span_exporter = OTLPSpanExporter()
else:
    span_exporter = ConsoleSpanExporter() # For local development

if os.getenv("ICE_TELEMETRY_ENABLED", "true").lower() == "true":
    span_processor = ErrorOnlySpanProcessor(span_exporter)
    provider.add_span_processor(span_processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# --- STRUCTURED PRODUCTION LOGGING ---
os.makedirs(".logs", exist_ok=True)
log_file = ".logs/ice.log"

class StructuredLogger(logging.Handler):
    def emit(self, record):
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None
        
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "trace_id": format(span_context.trace_id, "032x") if span_context and span_context.trace_id else None,
            "span_id": format(span_context.span_id, "016x") if span_context and span_context.span_id else None,
        }
        serialized = orjson.dumps(log_entry).decode()
        print(serialized)
        with open(log_file, "a") as f:
            f.write(serialized + "\n")

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [StructuredLogger()]
logger = logging.getLogger("ice_engine")

app = FastAPI(
    title="ICE (Indexless Context Engine)",
    description="Universal Protocol Proxy for Unbounded Context, Tools, and Anthropic compatibility.",
    version="3.0.0"
)
print(f"DEBUG: App object created with ID: {id(app)}")

# --- ROUTES ---

@app.get("/v1")
async def v1_status():
    if ice_server.degraded_mode: return JSONResponse(status_code=503, content={"message": "We're Hot as Lava", "status": "degraded"})
    return {"message": "We're Cold as ICE", "status": "healthy"}

@app.get("/")
async def root_status(): return await v1_status()

@app.get("/live")
async def live_probe():
    """
    Kubernetes Liveness Probe.
    Indicates that the application is running.
    """
    return JSONResponse(status_code=200, content={"status": "live", "message": "ICE is running"})

@app.get("/ready")
async def ready_probe():
    """
    Kubernetes Readiness Probe.
    Checks if the application is ready to serve traffic (e.g., connected to DB and Redis).
    """
    db_ready = False
    redis_ready = False

    try:
        if ice_server.db_pool:
            async with ice_server.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ready = True
        else:
            db_ready = os.getenv("ICE_SKIP_INFRA_CONNECT") == "1"
    except Exception:
        db_ready = False

    try:
        if ice_server.redis:
            await ice_server.redis.ping()
            redis_ready = True
        else:
            redis_ready = os.getenv("ICE_SKIP_INFRA_CONNECT") == "1"
    except Exception:
        redis_ready = False

    if db_ready and redis_ready:
        return JSONResponse(status_code=200, content={"status": "ready", "message": "ICE is ready to serve traffic"})
    else:
        return JSONResponse(status_code=503, content={"status": "not_ready", "message": "ICE is not ready to serve traffic", "db_ready": db_ready, "redis_ready": redis_ready})


@app.middleware("http")
async def handle_server_state_middleware(request: Request, call_next):
    if is_shutting_down:
        return JSONResponse(status_code=503, content={"error": {"code": 503, "message": "Server is shutting down."}})
    
    response = await call_next(request)

    if ice_server.degraded_mode:
        response.headers["X-ICE-DEGRADED"] = "true; reason=DATABASE_UNREACHABLE"
    
    return response

# --- CONFIGURATION (Engine Tunables) ---
MEMORY_CAP_GB = float(os.getenv("ICE_MEMORY_CAP_GB", "30.0"))
MAX_CONCURRENT_STITCHES = int(os.getenv("ICE_MAX_STITCH_CONCURRENCY", "10"))
MAX_CONTINUATIONS = 5 # Hardcoded for memory retention test debugging
DB_MIN_POOL = int(os.getenv("ICE_DB_MIN_POOL", "5"))
DB_MAX_POOL = int(os.getenv("ICE_DB_MAX_POOL", "20"))
ICE_INTERNAL_API_KEY = os.getenv("ICE_INTERNAL_API_KEY", "super-secret-internal-key")
RETENTION_DAYS = int(os.getenv("ICE_RETENTION_DAYS", "30"))

# Global State for Graceful Shutdown
active_tasks = set()
shutdown_event = asyncio.Event()
is_shutting_down = False

STITCH_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_STITCHES)

STRUCTURED_PATTERNS = [
    r"<tool_call>", r"<mcp_.*>", r"<function", r'{"tool"',
    r'{"function"', r'{"functionCall"', r"<functionCall>", r"<thought>", r"<ice_plan>", r"<skill", r"call_"
]
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request", "message": "Validation error details", "detail": exc.errors(), "code": 400}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail.replace(" ", "_").lower(), "message": exc.detail, "code": exc.status_code}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred", "code": 500}
    )

# --- Models ---

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any]]
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    user: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class AnthropicContent(BaseModel):
    type: str
    text: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None
    content: Optional[Union[str, List[Any]]] = None # For tool_result

class AnthropicMessage(BaseModel):
    role: str
    content: Union[str, List[AnthropicContent]]

class AnthropicRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    system: Optional[Union[str, List[AnthropicContent]]] = None
    max_tokens: int = 4096
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class GeminiContentPart(BaseModel):
    text: Optional[str] = None

class GeminiContent(BaseModel):
    parts: List[GeminiContentPart]
    role: Optional[str] = None

class GeminiRequest(BaseModel):
    contents: List[GeminiContent]
    systemInstruction: Optional[Dict[str, Any]] = None
    generationConfig: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    toolConfig: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

@tracer.start_as_current_span("verify_tenant")
async def verify_tenant(
    authorization: Annotated[Optional[str], Header()] = None,
    x_session_id: Annotated[Optional[str], Header()] = None,
    x_user_id: Annotated[Optional[str], Header()] = None,
):
    api_key = None
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.split("Bearer ")[1]
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Authentication required: Missing Bearer Token.")

    session_id = x_session_id or "default-session"
    user_id = x_user_id or "default-user"
    
    # 1. Check Redis Cache for API Key -> Tenant Mapping (Fast Path)
    cache_key = f"auth:key:{hashlib.sha256(api_key.encode()).hexdigest()}"
    if not ice_server.degraded_mode and ice_server.redis:
        cached_tenant = await ice_server.redis.get(cache_key)
        if cached_tenant:
            tenant_id = cached_tenant.decode()
            if not await ice_server.rate_limiter.consume(tenant_id):
                raise HTTPException(status_code=429, detail="Rate limit exceeded for tenant.")
            return {"tenant_id": tenant_id, "session_id": session_id, "user_id": user_id, "api_key": api_key}

    # 2. Database/Secrets Manager Lookup and Tenant Limit Enforcement
    tenant_id = None
    try:
        # Get limits for the current license
        limits = get_current_license_limits()
        max_tenants = limits.get("max_tenants", float('inf'))

        # Check existing tenant from DB
        if not ice_server.degraded_mode and ice_server.db_pool:
            async with ice_server.db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT tenant_id FROM tenants WHERE api_key = $1", api_key)
                if row:
                    tenant_id = str(row["tenant_id"])

        # Fallback to Secrets Manager if not in DB
        if not tenant_id:
            secret_arn_prefix = os.getenv("ICE_SECRET_ARN_PREFIX")
            if secret_arn_prefix:
                sm_api_key_secret_string = await get_secret_from_aws_secrets_manager(f"{secret_arn_prefix}/{api_key}")
                if sm_api_key_secret_string:
                    try:
                        secret_data = orjson.loads(sm_api_key_secret_string)
                        tenant_id = str(secret_data.get("tenant_id", sm_api_key_secret_string))
                    except:
                        tenant_id = sm_api_key_secret_string

        # If tenant_id is still not found, it's either a dev key or a new tenant
        if not tenant_id:
            current_server_limits = get_current_license_limits()
            server_sku = current_server_limits.get("product", os.getenv("ICE_SKU", "ICE-DEVELOPMENT")) # Explicitly get SKU from env or license payload
            max_tenants_for_server_sku = current_server_limits.get("max_tenants", float('inf'))

            if api_key == "ice-default-key" and os.getenv("ICE_ALLOW_DEFAULT_KEY") == "1":
                tenant_id = "823dc24a-885e-4586-a74b-9144dcc0f849" # Default dev tenant
                tenant_sku = "ICE-DEVELOPMENT" # Default SKU for dev tenant
            else: # This is a genuinely new API key
                if not ice_server.degraded_mode and ice_server.db_pool:
                    async with ice_server.db_pool.acquire() as conn:
                        tenant_sku = server_sku # Use the SKU of the running ICE server for the new tenant

                        # Special check for ICE-COMMUNITY: Only one ICE-COMMUNITY tenant allowed globally.
                        if tenant_sku == "ICE-COMMUNITY":
                            community_tenant_count = await conn.fetchval(
                                "SELECT COUNT(*) FROM tenants WHERE sku = $1", "ICE-COMMUNITY"
                            )
                            if community_tenant_count >= 1: # Already one community tenant exists
                                logger.error(f"Free tier (ICE-COMMUNITY) limit reached globally.")
                                raise HTTPException(status_code=403, detail="Only one free tier license (ICE-COMMUNITY) is allowed per deployment.")

                        # Proceed with general tenant limit enforcement for the server's SKU
                        current_total_tenants = await conn.fetchval("SELECT COUNT(*) FROM tenants")
                        if current_total_tenants >= max_tenants_for_server_sku:
                            logger.error(f"Global tenant limit for server's SKU reached. SKU allows {max_tenants_for_server_sku}, trying to create {current_total_tenants + 1}.")
                            raise HTTPException(status_code=403, detail=f"Global tenant limit ({max_tenants_for_server_sku}) for this deployment's license tier has been reached.")

                        # Create new tenant
                        tenant_id = str(uuid.uuid4())
                        await conn.execute(
                            "INSERT INTO tenants (tenant_id, name, api_key, sku) VALUES ($1, $2, $3, $4)",
                            uuid.UUID(tenant_id), f"Tenant for {api_key[:8]}...", api_key, tenant_sku
                        )
                else:
                    # In degraded mode or without DB pool (shouldn't happen here if trying to create new tenant)
                    logger.warning(f"UNAUTHORIZED ACCESS ATTEMPT (degraded mode): API key '{api_key[:8]}...'")
                    raise HTTPException(status_code=401, detail="Invalid API Key.")
        
        # Apply rate limiting
        if not await ice_server.rate_limiter.consume(tenant_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded for tenant.")

        # Cache successful lookup for 5 minutes
        if not ice_server.degraded_mode and ice_server.redis and tenant_id:
            await ice_server.redis.set(cache_key, tenant_id, ex=300)

    except HTTPException: raise # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Security Critical: Auth System Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Authentication Error.")

    return {"tenant_id": tenant_id, "session_id": session_id, "user_id": user_id, "api_key": api_key}

# --- AUDIT LOGGING ---
audit_log_file = ".logs/audit.log"
os.makedirs(".logs", exist_ok=True)

async def log_audit_event(tenant_id: str, user_id: str, session_id: str, event_type: str, details: dict = None):
    """
    Writes an immutable audit log entry for compliance.
    """
    audit_entry = {
        "timestamp": time.time(),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": session_id,
        "event_type": event_type,
        "details": {k: (str(v) if not isinstance(v, (dict, list, str, int, float, bool, type(None))) else v) for k, v in (details or {}).items()}
    }
    # In a production system, this would write to a WORM (Write Once Read Many) drive or a dedicated audit database.
    # For this implementation, we append to a dedicated JSON log file.
    def _write_audit():
        with open(audit_log_file, "a") as f:
            f.write(orjson.dumps(audit_entry, default=lambda obj: str(obj)).decode() + "\n")
    
    await asyncio.to_thread(_write_audit)

# --- Core Service Container ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://ice_user:ice_password@localhost:5432/ice_db")
from .core.pager import ContextPager, EmbeddingModel
from .core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .core.rate_limit import TokenBucketRateLimiter
from .core.metrics import (
    ICE_TOTAL_QUERIES, ICE_EMBEDDING_CACHE_HITS, ICE_EMBEDDING_CACHE_MISSES,
    ICE_GENERATION_LATENCY, ICE_DB_POOL_ACQUIRED, ICE_DB_POOL_AVAILABLE
)
try:
    from ice.build_config import RAG_MODE as COMPILED_RAG_MODE
except ImportError:
    COMPILED_RAG_MODE = "local"

def get_current_license_limits():
    """Dynamically returns the tier-specific limits based on active SKU."""
    license_payload = ice_server.security.license_payload if hasattr(ice_server.security, 'license_payload') and ice_server.security and ice_server.security.license_payload else {}
    
    sku = license_payload.get("product", os.getenv("ICE_SKU", "ICE-DEVELOPMENT"))
    
    # Defaults for Development / Unknown
    limits = {
        "max_nodes": float('inf'),
        "max_tenants": float('inf'),
        "max_concurrent_sessions": float('inf'),
        "max_tokens_per_session": float('inf'),
        "max_users": float('inf'), # Added for completeness
    }

    if sku == "ICE-COMMUNITY":
        limits.update({
            "max_nodes": 1,
            "max_tenants": 1,
            "max_concurrent_sessions": 1,
            "max_tokens_per_session": 10_000_000,
            "max_users": 1,
        })
    elif sku == "ICE-DEVELOPER-PRO":
        limits.update({
            "max_nodes": 3,
            "max_tenants": 3,
            "max_concurrent_sessions": 10,
            "max_tokens_per_session": 100_000_000,
            "max_users": float('inf'), # Dev Pro has unlimited users but limited tenants
        })
            "max_tokens_per_session": license_payload.get("max_tokens_per_session", float('inf')),
            "max_users": license_payload.get("max_users", float('inf')),
        })
    
    return limits

@asynccontextmanager
async def track_concurrent_session(tenant_id: str):
    """Enforces concurrent session limits per tenant using Redis."""
    limits = get_current_license_limits()
    max_concurrent = limits.get("max_concurrent_sessions", float('inf'))
    
    session_key = f"active_sessions:{tenant_id}"
    
    if ice_server.degraded_mode or not ice_server.redis or max_concurrent == float('inf'):
        yield
        return
        
    try:
        # Increment and get current count
        current_sessions = await ice_server.redis.incr(session_key)
        # Set expiry to prevent leaks (e.g., if a process dies unexpectedly)
        await ice_server.redis.expire(session_key, 3600) 
        
        if current_sessions > max_concurrent:
            # Revert the increment since we're rejecting
            await ice_server.redis.decr(session_key)
            raise HTTPException(
                status_code=429, 
                detail=f"Concurrent session limit ({max_concurrent}) for your license tier has been reached."
            )
            
        yield
        
    finally:
        # Always decrement when the session is complete, but ensure we don't go below 0
        if not ice_server.degraded_mode and ice_server.redis:
            current = await ice_server.redis.get(session_key)
            if current and int(current) > 0:
                await ice_server.redis.decr(session_key)

class ICEServer:
    def __init__(self):
        self.db_pool = None
        self.redis = None
        self.security = None # To hold the SecurityManager instance
        self.embedder = EmbeddingModel() # Instantiate embedder here
        self.pager = ContextPager(self.embedder)
        self.reasoning = ReasoningManager(self.db_pool, self.redis)
        self.episodic = EpisodicManager(self.db_pool, self.redis)
        self.ingestion = IngestionPipeline(self.episodic, self.embedder) # Pass embedder
        self.http_client = None
        self.degraded_mode = False
        self.lib = None # RCC FFI Library

        # --- Circuit Breakers for Upstream LLMs ---
        self.ollama_breaker = CircuitBreaker(name="ollama_breaker", failure_threshold=3, recovery_timeout=60)
        self.openai_breaker = CircuitBreaker(name="openai_breaker", failure_threshold=3, recovery_timeout=60)
        self.anthropic_breaker = CircuitBreaker(name="anthropic_breaker", failure_threshold=3, recovery_timeout=60)
        self.gemini_breaker = CircuitBreaker(name="gemini_breaker", failure_threshold=3, recovery_timeout=60)

        # --- Rate Limiter ---
        self.rate_limiter = TokenBucketRateLimiter(
            capacity=int(os.getenv("ICE_RATELIMIT_CAPACITY", "100")),
            refill_rate=float(os.getenv("ICE_RATELIMIT_REFILL_RATE", "10.0"))
        )
    async def startup(self):
        with tracer.start_as_current_span("ICEServer.startup"): # Trace startup
            
            try:
                # --- PHASE 0: Load RCC Core Library ---
                self.lib = get_lib()
                if self.lib is None:
                    raise RuntimeError("❌ CRITICAL ERROR: RCC Core Library could not be loaded. ICE V3 requires the Resonant C Compiler (RCC) core.")
                logger.info("ICE CORE: Successfully loaded RCC FFI Core Library.")

                # Determine RAG Architecture Mode (External vs Local)
                try:
                    from ice.build_config import RAG_MODE as COMPILED_RAG_MODE
                    rag_mode = COMPILED_RAG_MODE
                except ImportError:
                    rag_mode = os.getenv("RAG_MODE", "local")
                
                os.environ["RAG_MODE"] = rag_mode 
                architecture_name = "ICE Cloud" if rag_mode == "external" else "ICE Local"
                logger.info(f"ICE CORE: Booting Unified Memory Engine: {architecture_name}")
                trace.get_current_span().set_attribute("ice.architecture_mode", rag_mode)
                
                # Verify Telemetry Pipeline
                telemetry_status = "ENABLED" if os.getenv("ICE_TELEMETRY_ENABLED", "true").lower() == "true" else "DISABLED (Privacy Mode)"
                logger.info(f"ICE CORE: Global Telemetry Pipeline is {telemetry_status}")
                trace.get_current_span().set_attribute("ice.telemetry_status", telemetry_status)

                # --- PHASE 2: CONNECT INFRASTRUCTURE ---
                try:
                    with tracer.start_as_current_span("db_connection"): # Trace DB connection
                        if not self.db_pool and os.getenv("ICE_SKIP_INFRA_CONNECT") != "1":
                            self.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=DB_MIN_POOL, max_size=DB_MAX_POOL)
                    with tracer.start_as_current_span("redis_connection"): # Trace Redis connection
                        if not self.redis and os.getenv("ICE_SKIP_INFRA_CONNECT") != "1":
                            self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                except Exception as infra_err:
                    logger.error(f"ICE CORE: Infrastructure connection failed: {infra_err}")
                    self.degraded_mode = True # ALWAYS set degraded mode on failure

                # Initialize Core Managers (Even if pools are None, managers should exist)
                self.reasoning = ReasoningManager(self.db_pool, self.redis)
                self.episodic = EpisodicManager(self.db_pool, self.redis)
                self.ingestion = IngestionPipeline(self.episodic, self.embedder) # Pass embedder
                
                # CRITICAL: Verify embedder initialization
                if not hasattr(self.embedder, 'session') or self.embedder.session is None:
                    logger.error("ICE CORE: EmbeddingModel failed to initialize its ONNX session. Entering degraded mode.")
                    self.degraded_mode = True
                if not hasattr(self.embedder, 'tokenizer') or self.embedder.tokenizer is None:
                    logger.error("ICE CORE: EmbeddingModel failed to initialize its tokenizer. Entering degraded mode.")
                    self.degraded_mode = True

                logger.info("ICE CORE: Systems online.")
            except Exception as e:
                logger.error(f"ICE CORE: Critical startup failure: {e}", exc_info=True)
                trace.get_current_span().set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                self.degraded_mode = True

            limits = httpx.Limits(max_keepalive_connections=100, max_connections=1000)
            self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0), limits=limits)

    async def shutdown(self):
        with tracer.start_as_current_span("ICEServer.shutdown"): # Trace shutdown
            if self.http_client: await self.http_client.aclose()
            if self.db_pool: await self.db_pool.close()

ice_server = ICEServer()

def get_ollama_base():
    url = os.getenv("UPSTREAM_API_URL", "http://localhost:11434/v1/chat/completions")
    if os.path.exists("/.dockerenv") and "localhost" in url:
        return "http://host.docker.internal:11434"
    return url.replace("/v1/chat/completions", "").replace("/v1/completions", "")


@tracer.start_as_current_span("retention_purge_loop_start")
async def retention_purge_loop():
    """
    Background loop that triggers the retention policy every 24 hours.
    """
    while True:
        with tracer.start_as_current_span("retention_purge_cycle"): # Trace each cycle
            try:
                if ice_server.episodic and ice_server.reasoning:
                    logger.info(f"Retention Engine: Starting daily maintenance (Policy: {RETENTION_DAYS} days)...")
                    await asyncio.gather(
                        ice_server.episodic.purge_expired_ledger(RETENTION_DAYS),
                        ice_server.reasoning.purge_expired_traces(RETENTION_DAYS),
                        return_exceptions=True
                    )
                    logger.info("Retention Engine: Daily maintenance complete.")
                else:
                    logger.warning("Retention Engine: Core managers not initialized. Skipping maintenance cycle.")
            except Exception as e:
                logger.error(f"Retention Engine Error: {e}")
                trace.get_current_span().set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            # Wait for 24 hours
            await asyncio.sleep(86400)

@tracer.start_as_current_span("db_metrics_loop_start")
async def db_metrics_loop():
    """
    Background loop that updates PostgreSQL connection pool metrics.
    """
    while True:
        try:
            if ice_server.db_pool:
                stats = ice_server.db_pool.get_stats()
                ICE_DB_POOL_ACQUIRED.set(stats.connections)
                ICE_DB_POOL_AVAILABLE.set(stats.maxsize - stats.connections)
            else:
                ICE_DB_POOL_ACQUIRED.set(0)
                ICE_DB_POOL_AVAILABLE.set(0)
        except Exception as e:
            logger.error(f"DB Metrics Loop Error: {e}", exc_info=True)
        await asyncio.sleep(10) # Update every 10 seconds

@app.on_event("startup")
async def startup_event():
    global is_shutting_down
    # Startup logic
    if os.getenv("ICE_TEST_MODE") != "1":
        ice_server.security = enforce_licensing()
    
    await ice_server.startup()
    if ice_server.episodic:
        asyncio.create_task(retention_purge_loop())
    if ice_server.db_pool:
        asyncio.create_task(db_metrics_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global is_shutting_down
    is_shutting_down = True
    logger.info(f"Graceful shutdown initiated. Waiting for {len(active_tasks)} active tasks to complete...")
    if active_tasks:
        await asyncio.wait(active_tasks, timeout=30) # Wait up to 30 seconds
    await ice_server.shutdown()

@tracer.start_as_current_span("get_cached_embedding")
async def get_cached_embedding(text: str) -> List[float]:
    if not isinstance(text, str) or not text.strip():
        logger.warning(f"get_cached_embedding: Invalid or empty text, returning zero vector.")
        return [0.0] * 384
    
    if ice_server.degraded_mode: 
        logger.warning(f"get_cached_embedding: Returning zero vector due to degraded_mode=True.")
        return [0.0] * 384
    try:
        if ice_server.redis:
            h = hashlib.sha256(text.encode()).hexdigest()
            key = f"embed:{h}"
            cached = await ice_server.redis.get(key)
            if cached: 
                ICE_EMBEDDING_CACHE_HITS.inc()
                return orjson.loads(cached)
        
        ICE_EMBEDDING_CACHE_MISSES.inc()
        vec = await ice_server.pager.embedder.embed_async(text)
        
        if ice_server.redis:
            await ice_server.redis.set(key, orjson.dumps(vec), ex=86400)
        return vec
    except Exception as e: 
        logger.error(f"Embedding caching error: {e}", exc_info=True)
        return [0.0] * 384

@tracer.start_as_current_span("generate_ice_chunks")
async def generate_ice_chunks(
    model, messages, temperature, max_tokens, 
    tenant_id, session_id, user_id, client_api_key, 
    options=None, tools=None, tool_choice=None, response_format=None,
    client_config: Optional[Dict[str, Any]] = None, # From Python SDK
    headers: Optional[Dict[str, str]] = None # From Node.js SDK
):
    start_time = time.time()
    try:
        # --- Dynamic Configuration Loading ---
        # Prioritize: 1. HTTP Headers (Node.js), 2. Client Config (Python SDK), 3. Environment Vars, 4. Hardcoded Defaults
        def get_dynamic_config(key_env, key_client_config, key_header, default_value, type_cast=str):
            if headers and f"X-Ice-{key_header}" in headers:
                return type_cast(headers[f"X-Ice-{key_header}"])
            if client_config and key_client_config in client_config:
                return type_cast(client_config[key_client_config])
            return type_cast(os.getenv(key_env, str(default_value)))


        # Fetch all tunable parameters
        dynamic_memory_cap_gb = get_dynamic_config("ICE_MEMORY_CAP_GB", "memory_cap_gb", "Memory-Cap-Gb", 30.0, float)
        dynamic_max_stitch_concurrency = get_dynamic_config("ICE_MAX_STITCH_CONCURRENCY", "max_stitch_concurrency", "Max-Stitch-Concurrency", 10, int)
        dynamic_retention_days = get_dynamic_config("ICE_RETENTION_DAYS", "retention_days", "Retention-Days", 30, int)
        dynamic_chunk_size = get_dynamic_config("ICE_CHUNK_SIZE", "chunk_size", "Chunk-Size", 12000, int)
        dynamic_max_input_tokens = get_dynamic_config("ICE_POST_LIMIT", "max_input_tokens", "Max-Input-Tokens", 128000, int)
        dynamic_chunk_overlap = get_dynamic_config("ICE_CHUNK_OVERLAP", "chunk_overlap", "Chunk-Overlap", 1000, int)
        dynamic_max_continuations = get_dynamic_config("ICE_MAX_CONTINUATIONS", "max_continuations", "Max-Continuations", 10, int)
        dynamic_priority_memory_limit = get_dynamic_config("ICE_PRE_LIMIT", "priority_memory_limit", "Priority-Memory-Limit", 5, int)
        dynamic_reasoning_recall_limit = get_dynamic_config("ICE_REASONING_RECALL_LIMIT", "reasoning_recall_limit", "Reasoning-Recall-Limit", 10, int)
        dynamic_privacy_masking = get_dynamic_config("ICE_PRIVACY_MASKING", "privacy_masking", "Privacy-Masking", "none", str)
        dynamic_llm_routing_strategy = get_dynamic_config("ICE_LLM_ROUTING_STRATEGY", "llm_routing_strategy", "LLM-Routing-Strategy", "best-available", str)

        # Apply dynamic concurrency limit
        STITCH_SEMAPHORE._value = dynamic_max_stitch_concurrency
        logger.debug(f"Stitcher: Dynamic MAX_STITCH_CONCURRENCY set to {dynamic_max_stitch_concurrency}")

        # Pass dynamic tunables to pager and other managers
        ice_server.pager.chunk_size = dynamic_chunk_size
        ice_server.pager.chunk_overlap = dynamic_chunk_overlap
        ice_server.pager.max_input_tokens = dynamic_max_input_tokens # Update pager's context window
        ice_server.episodic.priority_memory_limit = dynamic_priority_memory_limit
        ice_server.reasoning.recall_limit = dynamic_reasoning_recall_limit

        # Routing strategy and privacy masking can be handled here for specific logic if needed
        if dynamic_privacy_masking == "strict":
            logger.debug("Stitcher: Strict privacy masking enabled for this request.")
        if dynamic_llm_routing_strategy == "cloud-fallback":
            logger.debug("Stitcher: Routing strategy set to cloud-fallback.")

        logger.debug(f"Stitcher: Starting chunk generation loop. Model: {model}, Session: {session_id}")
        current_req = [messages[-1]]
        history = messages[:-1]
        query_text = current_req[-1].get("content", "")
        if isinstance(query_text, list):
            query_text = " ".join([item.get("text", "") for item in query_text if item.get("type") == "text"])

        # --- PRODUCTION RLS ENFORCEMENT ---
        # We set the session-level tenant ID to ensure Postgres RLS policies are applied.
        async def set_rls_context(conn, current_tenant_id):
            if not ice_server.degraded_mode: # Only attempt to set RLS if not in degraded mode
                await conn.execute(f"SET LOCAL ice.current_tenant_id = '{current_tenant_id}'")

        # --- Audit Log: Chat Completion Started ---
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            event_type="chat_completion_started",
            details={"model": model, "initial_message": str(messages[-1]) if not isinstance(messages[-1], (dict, list, str, int, float, bool, type(None))) or 'MagicMock' in str(type(messages[-1])) else messages[-1]}
        )

        # --- Token Horizon Cap Enforcement ---
        limits = get_current_license_limits()
        max_tokens_per_session = limits.get("max_tokens_per_session", float('inf'))
    
        if not ice_server.degraded_mode and ice_server.episodic:
            try:
                # Save user message first
                user_message_embedding = await get_cached_embedding(query_text)
                await ice_server.episodic.save_message(
                    tenant_id, session_id, messages[-1]["role"], query_text, user_id=user_id, 
                    privacy_masking=dynamic_privacy_masking, embedding=user_message_embedding
                )

                current_session_tokens = await ice_server.episodic.get_session_token_count(tenant_id, session_id, user_id)
                if current_session_tokens > max_tokens_per_session:
                    raise HTTPException(status_code=403, detail=f"Token limit ({max_tokens_per_session}) for your license tier has been reached for this session.")
            except (HTTPException, ConnectionRefusedError, asyncpg.exceptions.ConnectionDoesNotExistError) as e:
                if isinstance(e, HTTPException):
                    raise # Re-raise HTTP exceptions
                logger.error(f"DB Error during token count/save: {e}. Entering DEGRADED MODE.")
                ice_server.degraded_mode = True
        retrieved_insights, traces = [], []
        try:
            query_vec = await get_cached_embedding(query_text)
            
            # Use Python retrieval fallback for now, as C search is just a stub
            async with ice_server.db_pool.acquire() as conn:
                 await set_rls_context(conn, tenant_id) # Pass tenant_id here
                 retrieved_insights = await ice_server.episodic.search_episodic(
                        tenant_id, query_vec, session_id=session_id, user_id=user_id,
                        limit=dynamic_priority_memory_limit, conn=conn
                 )
                 
                 reasoning_results = await ice_server.reasoning.search_reasoning(
                        tenant_id, query_vec, user_id=user_id,
                        limit=dynamic_reasoning_recall_limit
                 )
                 traces = [r["content"] for r in reasoning_results]

        except (ConnectionRefusedError, asyncpg.exceptions.ConnectionDoesNotExistError) as e:
            logger.error(f"Retrieval Error (Connection Failed): {e}. Entering DEGRADED MODE.")
            ice_server.degraded_mode = True
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")

        if os.getenv("ICE_MOCK_LLM_CALL") == "1":
            logger.info("Stitcher: MOCK LLM CALL ENABLED. Returning retrieved insights.")
            mock_content = "This is a mock response."
            if retrieved_insights:
                mock_content += f" Insights: {' | '.join(retrieved_insights)}"
            yield {"choices": [{"delta": {"content": mock_content}}]}
            await asyncio.sleep(0.1)
            yield "[DONE]"
            return

        # --- Audit Log: Memory Retrieved ---
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            event_type="memory_retrieved",
            details={
                "query_text": query_text,
                "insights_count": len(retrieved_insights),
                "traces_count": len(traces)
            }
        )

        def resolve_routing(m_id):
            m_low = m_id.lower()
            if any(k in m_low for k in ["gpt-4", "gpt-3.5", "openai"]):
                return os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions"), os.getenv("OPENAI_API_KEY", ""), ice_server.openai_breaker
            if any(k in m_low for k in ["claude", "anthropic"]):
                return os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"), os.getenv("ANTHROPIC_API_KEY", ""), ice_server.anthropic_breaker
            if any(k in m_low for k in ["gemini", "google"]):
                return os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"), os.getenv("GEMINI_API_KEY", ""), ice_server.gemini_breaker
            
            return f"{get_ollama_base()}/v1/chat/completions", "", ice_server.ollama_breaker

        upstream_url, env_api_key, breaker = resolve_routing(model)
        api_key_to_use = client_api_key if client_api_key else env_api_key

        headers = {"Authorization": f"Bearer {api_key_to_use}"} if api_key_to_use else {}
        if "anthropic.com" in upstream_url:
            headers = {"x-api-key": api_key_to_use, "anthropic-version": "2023-06-01", "content-type": "application/json"}

        continuations = 0
        total_completion_tokens = 0
        full_stitched_content = ""
        turn_limit = dynamic_max_continuations
        target_tokens = options.get("max_tokens", dynamic_max_input_tokens) if options else dynamic_max_input_tokens
    
        logger.info(f"Stitcher: Initialized loop. turn_limit: {turn_limit}, target_tokens: {target_tokens}")

        async with STITCH_SEMAPHORE:
            extractor = ReasoningExtractor()
            while continuations < turn_limit:
                logger.debug(f"Stitcher: Starting turn {continuations+1}/{turn_limit}. Total tokens: {total_completion_tokens}.")
                current_history = history.copy()
                if full_stitched_content:
                    current_history.append({"role": "assistant", "content": full_stitched_content})
                    if target_tokens > 0:
                        modified_req = [{"role": "user", "content": f"You have reached {total_completion_tokens} tokens out of the required {target_tokens} tokens. DO NOT write a conclusion yet. Continue exactly where you left off. Do not acknowledge this."}]
                    else:
                        modified_req = [{"role": "user", "content": "Continue exactly where you left off."}]
                else:
                    modified_req = current_req

                # Always use Python-based assembly for now to avoid FFI stability issues
                final_prompt_dicts, token_count, output_budget = ice_server.pager.assemble_prompt(
                    current_request=modified_req,
                    historical_messages=current_history,
                    retrieved_insights=retrieved_insights,
                    reasoning_traces=traces,
                    model_id=model,
                    max_input_tokens=dynamic_max_input_tokens,
                )                
                payload = {
                    "model": model, "messages": final_prompt_dicts, "stream": True,
                    "temperature": temperature, 
                    "max_tokens": max_tokens or 2048
                }
                if tools: payload["tools"] = tools
                if tool_choice: payload["tool_choice"] = tool_choice
                if response_format: payload["response_format"] = response_format

                if "ollama" in upstream_url:
                    payload["options"] = {"num_ctx": dynamic_max_input_tokens, "num_predict": -1}
                    if options: payload["options"].update(options)
                elif options:
                    payload.update({k: v for k, v in options.items() if k not in payload})

                last_finish_reason, turn_content = None, ""
                try:
                    async with breaker:
                        async with ice_server.http_client.stream("POST", upstream_url, json=payload, headers=headers) as response:
                            if response.status_code != 200:
                                # ... (error handling unchanged)
                                err_txt = ""
                                try:
                                    err_txt = (await response.aread()).decode("utf-8")
                                except Exception:
                                    pass
                                logger.error(f"Stitcher: Upstream HTTP error: {response.status_code}. Response: {err_txt}.")
                                yield {"error": {"message": f"Upstream error {response.status_code}", "code": response.status_code}}; return

                            async for line in response.aiter_lines():
                                if isinstance(line, bytes):
                                    line = line.decode('utf-8')
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str.strip() == "[DONE]": continue 
                                    try:
                                        chunk = orjson.loads(data_str)
                                        choice = chunk.get("choices", [{}])[0]
                                        delta = choice.get("delta", {}).get("content", "")
                                        last_finish_reason = choice.get("finish_reason")
                                        
                                        if delta:
                                            # [PHASE 33]: REAL-TIME REASONING EXTRACTION
                                            visible_text, extracted_traces = extractor.process_chunk(delta)
                                            
                                            # 1. Save and stream thoughts
                                            for tag, content in extracted_traces:
                                                if not ice_server.degraded_mode:
                                                    asyncio.create_task(ice_server.reasoning.save_trace(
                                                        tenant_id, session_id, content, user_id=user_id, metadata={"tag": tag}
                                                    ))
                                                yield {"choices": [{"delta": {"content": f"<thought>{content}</thought>"}}]}
                                            
                                            # 2. Process and yield visible text
                                            if visible_text:
                                                turn_content += visible_text
                                                full_stitched_content += visible_text
                                                total_completion_tokens += len(visible_text) // 4
                                                
                                                chunk["choices"][0]["delta"]["content"] = visible_text
                                                chunk["x_ice_meta"] = {
                                                    "turn": continuations + 1,
                                                    "total_completion_tokens": total_completion_tokens,
                                                    "target_tokens": target_tokens,
                                                    "turn_limit": turn_limit
                                                }
                                                yield chunk
                                        elif last_finish_reason:
                                            chunk["x_ice_meta"] = {
                                                "turn": continuations + 1,
                                                "total_completion_tokens": total_completion_tokens,
                                                "target_tokens": target_tokens,
                                                "turn_limit": turn_limit
                                            }
                                            yield chunk
                                    except orjson.JSONDecodeError: continue
                                    except Exception as e:
                                        logger.error(f"Stitcher: Unexpected chunk processing error: {e}")
                except CircuitBreakerOpen:
                    logger.error(f"Stitcher: Upstream service '{breaker.name}' is unavailable. Circuit breaker is open.")
                    yield {"error": {"message": f"Upstream service unavailable: {breaker.name}", "code": 503}}; return
                
                # Flush extractor at end of turn to catch trailing text
                final_text, final_traces = extractor.flush()
                if final_text:
                    turn_content += final_text
                    full_stitched_content += final_text
                for tag, content in final_traces:
                    if not ice_server.degraded_mode:
                        asyncio.create_task(ice_server.reasoning.save_trace(
                            tenant_id, session_id, content, user_id=user_id, metadata={"tag": tag}
                        ))
                
                # --- TERMINATION LOGIC ---
                logger.debug(f"Stitcher: Evaluating termination. Last finish reason: {last_finish_reason}, Total tokens: {total_completion_tokens}, Continuations: {continuations}, Turn limit: {turn_limit}")
                if last_finish_reason in ["tool_calls", "function_call", "content_filter"]:
                    logger.info(f"Stitcher: Terminating due to structured pattern/content filter: {last_finish_reason}.")
                    break
                if any(re.search(p, turn_content) for p in STRUCTURED_PATTERNS):
                    logger.info(f"Stitcher: Terminating due to structured pattern in content.")
                    break


                if last_finish_reason in ["stop"]:
                    logger.info(f"Stitcher: Terminating because LLM finished naturally (reason: stop).")
                    break
                    
                if continuations + 1 >= turn_limit:
                    logger.info(f"Stitcher: Reached turn_limit ({turn_limit}). Terminating stitching loop.")
                    break

                if not turn_content:
                    logger.warning("Stitcher: No content received in turn. Terminating loop.")
                    break 

                # Progressive persistence
                if not ice_server.degraded_mode:
                    await ice_server.episodic.save_message(
                        tenant_id, session_id, "assistant", turn_content, user_id=user_id
                    )
                logger.info(f"Stitcher: End of turn {continuations+1}. Finish reason: {last_finish_reason}. Content length: {len(turn_content)}. Total tokens: {total_completion_tokens}.")
                
                continuations += 1
                logger.info(f"ICE STITCHING: Turn {continuations}/{turn_limit} (Tokens: {total_completion_tokens}/inf)")

        final_chunk = {"id": f"ice-{int(time.time())}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        final_chunk["x_ice_meta"] = {
            "turn": continuations + 1,
            "total_completion_tokens": total_completion_tokens,
            "target_tokens": target_tokens,
            "turn_limit": turn_limit
        }

        # --- Meter Usage ---
        if hasattr(ice_server.security, 'license_arn'):
            asyncio.create_task(meter_usage(ice_server.security.license_arn, total_completion_tokens))

        yield final_chunk
        await asyncio.sleep(0.1)
        yield "[DONE]"
    finally:
        duration = time.time() - start_time
        ICE_GENERATION_LATENCY.observe(duration)

@app.post("/v1/internal/search", include_in_schema=False)
async def internal_search(request: InternalSearchRequest, _=Depends(verify_internal_api_key)):
    """
    Internal endpoint for federated search.
    """
    if ice_server.degraded_mode:
        return JSONResponse(status_code=503, content={"message": "Service Degraded", "results": []})
    
    try:
        results = await ice_server.episodic.search_local_episodic(
            tenant_id=request.tenant_id,
            query_vector=request.query_vector,
            session_id=request.session_id,
            user_id=request.user_id,
            limit=request.limit
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Internal Search Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e), "results": []})

@app.post("/v1/ingest")
async def ingest_document_proxy(file_path: str, context: dict = Depends(verify_tenant)):
    """
    Ingests a document or folder into the tenant's indexless context pool.
    """
    if ice_server.degraded_mode: return JSONResponse(status_code=503, content={"message": "Service Degraded"})
    
    # --- LFI / PATH TRAVERSAL PREVENTION ---
    base_dir = os.path.abspath(os.getenv("ICE_UPLOAD_DIR", "./uploads"))
    # Ensure base directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    target_path = os.path.abspath(os.path.join(base_dir, file_path))
    
    if not target_path.startswith(base_dir):
        return JSONResponse(status_code=403, content={"success": False, "error": "Path traversal detected."})
        
    if not os.path.exists(target_path):
        return JSONResponse(status_code=404, content={"success": False, "error": "File not found in upload directory."})
        
    try:
        count = ice_server.lib.rcc_ingest_document(
            context["tenant_id"].encode('utf-8'),
            context["user_id"].encode('utf-8'),
            target_path.encode('utf-8')
        )
        # --- Audit Log: Document Ingested ---
        await log_audit_event(
            tenant_id=context["tenant_id"],
            user_id=context["user_id"],
            session_id=context["session_id"], # Associate ingestion with a session if applicable
            event_type="document_ingested",
            details={"file_path": file_path, "chunks_ingested": count}
        )
        return {"success": True, "chunks_ingested": count, "message": f"Successfully paged {target_path} into memory."}
    except Exception as e:
        logger.error(f"Ingest Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/v1/health")
async def health():
    # Health check is public for load balancer heartbeats
    if ice_server.degraded_mode:
        return JSONResponse(status_code=503, content={"message": "We're Hot as Lava", "status": "degraded", "ver": "3.0.0"})
    
    ram = psutil.virtual_memory()
    usage_gb = ram.used / (1024**3)
    
    status = "healthy"
    if usage_gb > (MEMORY_CAP_GB * 0.9): # Warning at 90% of cap
        logger.warning(f"MEMORY ALERT: ICE is approaching the configured memory limit ({usage_gb:.1f}GB / {MEMORY_CAP_GB}GB)")
        status = "warn_memory_pressure"

    return {
        "message": "We're Cold as ICE" if status == "healthy" else "System under pressure",
        "status": status,
        "usage_gb": f"{usage_gb:.1f}GB",
        "memory_cap_gb": f"{MEMORY_CAP_GB}GB",
        "active_concurrency_limit": MAX_CONCURRENT_STITCHES,
        "ver": "3.0.0"
    }

@app.websocket("/v1/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket Engine (v3.1.75)
    Strictly verified and rate-limited for agentic pools.
    """
    ICE_TOTAL_QUERIES.inc() # Increment total queries for Prometheus
    await websocket.accept()
    client_host = websocket.client.host
    session_id = "unknown"
    try:
        # Initial handshake to receive configuration/headers
        data = await websocket.receive_text()
        req_json = orjson.loads(data)
        
        # --- Mandatory Security Handshake ---
        api_key = req_json.get("api_key")
        if not api_key:
            await websocket.send_text(orjson.dumps({"error": "Unauthorized: Missing api_key in handshake."}).decode())
            await websocket.close(code=1008)
            return

        # Perform strict tenant verification
        try:
            auth_context = await verify_tenant(
                authorization=f"Bearer {api_key}",
                x_session_id=req_json.get("session_id"),
                x_user_id=req_json.get("user_id")
            )
        except Exception as auth_error:
            await websocket.send_text(orjson.dumps({"error": f"Authentication failed: {auth_error}"}).decode())
            await websocket.close(code=1008)
            return

        tenant_id = auth_context["tenant_id"]
        session_id = auth_context["session_id"]
        user_id = auth_context["user_id"]
        model = req_json.get("model", "ministral-3:3b")
        messages = req_json.get("messages", [])
        
        logger.info(f"WS_OPEN: Session {session_id} for User {user_id} (Tenant: {tenant_id[:8]}) from {client_host}")

        # The WebSocket stream must respect the same Stitching Semaphore as REST
        async with STITCH_SEMAPHORE:
            async with track_concurrent_session(tenant_id):
                async for chunk in generate_ice_chunks(
                    model, messages, 0.7, 4096, 
                    tenant_id, session_id, user_id, api_key, 
                    options=req_json.get("options"), # Options are still passed
                    headers=websocket.headers # Pass the websocket headers
                ):
                    if chunk == "[DONE]":
                        await websocket.send_text("data: [DONE]\n\n")
                        break
                    await websocket.send_text(f"data: {orjson.dumps(chunk).decode()}\n\n")
            
    except WebSocketDisconnect:
        logger.info(f"WS_DISCONNECT: Session {session_id} closed by client.")
    except Exception as e:
        logger.error(f"WS_FATAL_ERROR: {e}")
        try:
            await websocket.send_text(orjson.dumps({"error": str(e)}).decode())
            await websocket.close(code=1011)
        except: pass
    finally:
        logger.debug(f"WS_CLEANUP: Resources released for session {session_id}")

@app.post("/v1/chat/completions")
async def chat_completions_proxy(fastapi_request: Request, request: ChatCompletionRequest, context: dict = Depends(verify_tenant)):
    ICE_TOTAL_QUERIES.inc() # Increment total queries for Prometheus
    messages_dicts = [m.model_dump() for m in request.messages]
    if request.stream:
        async def stream_gen():
            async with track_concurrent_session(context["tenant_id"]):
                async for chunk in generate_ice_chunks(
                    request.model, messages_dicts, request.temperature, request.max_tokens, 
                    context["tenant_id"], context["session_id"], context["user_id"], context["api_key"], 
                    options=request.options, tools=request.tools, tool_choice=request.tool_choice, response_format=request.response_format,
                    headers=fastapi_request.headers # Pass the request headers
                ):
                    if chunk == "[DONE]": yield "data: [DONE]\n\n"
                    else: yield f"data: {orjson.dumps(chunk).decode()}\n\n"
        return StreamingResponse(stream_gen(), media_type="text/event-stream")
    
    accumulated = ""
    async with track_concurrent_session(context["tenant_id"]):
        async for chunk in generate_ice_chunks(
            request.model, messages_dicts, request.temperature, request.max_tokens, 
            context["tenant_id"], context["session_id"], context["user_id"], context["api_key"], 
            options=request.options, tools=request.tools, tool_choice=request.tool_choice, response_format=request.response_format,
            headers=fastapi_request.headers # Pass the request headers
        ):
            if isinstance(chunk, dict) and "error" in chunk:
                return JSONResponse(status_code=502, content=chunk)
            if chunk != "[DONE]":
                accumulated += chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
    return {"id": f"ice-{int(time.time())}", "object": "chat.completion", "created": int(time.time()), "model": request.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": accumulated}, "finish_reason": "stop"}], "usage": {"completion_tokens": len(accumulated)//4, "total_tokens": len(accumulated)//4}}

@app.post("/v1/messages")
async def anthropic_messages_proxy(fastapi_request: Request, request: AnthropicRequest, context: dict = Depends(verify_tenant)):
    ICE_TOTAL_QUERIES.inc() # Increment total queries for Prometheus
    adapter = get_provider_adapter(provider_hint="anthropic")
    openai_msgs = []
    if request.system:
        openai_msgs.append({"role": "system", "content": adapter.map_multimodal_content(request.system)})
    
    for m in request.messages:
        openai_msgs.append({"role": m.role, "content": adapter.map_multimodal_content(m.content)})

    if request.stream:
        async def anthropic_stream_gen():
            msg_id = f"ice-msg-{int(time.time())}"
            yield f"event: message_start\ndata: {orjson.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': request.model, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}}).decode()}\n\n"
            yield f"event: content_block_start\ndata: {orjson.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}).decode()}\n\n"
            async with track_concurrent_session(context["tenant_id"]):
                async for chunk in generate_ice_chunks(
                    request.model, openai_msgs, request.temperature, request.max_tokens, 
                    context["tenant_id"], context["session_id"], context["user_id"], context["api_key"],
                    options=request.options, tools=request.tools, tool_choice=request.tool_choice,
                    headers=fastapi_request.headers # Pass the request headers
                ):
                    if chunk == "[DONE]": break
                    txt = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if txt: yield f"event: content_block_delta\ndata: {orjson.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': txt}}).decode()}\n\n"
            yield f"event: content_block_stop\ndata: {orjson.dumps({'type': 'content_block_stop', 'index': 0}).decode()}\n\n"
            yield f"event: message_delta\ndata: {orjson.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 0}}).decode()}\n\n"
            yield f"event: message_stop\ndata: {orjson.dumps({'type': 'message_stop'}).decode()}\n\n"
        return StreamingResponse(anthropic_stream_gen(), media_type="text/event-stream")

    accumulated = ""
    async with track_concurrent_session(context["tenant_id"]):
        async for chunk in generate_ice_chunks(
            request.model, openai_msgs, request.temperature, request.max_tokens, 
            context["tenant_id"], context["session_id"], context["user_id"], context["api_key"],
            options=request.options, tools=request.tools, tool_choice=request.tool_choice,
            headers=fastapi_request.headers # Pass the request headers
        ):
            if isinstance(chunk, dict) and "error" in chunk:
                return JSONResponse(status_code=502, content=chunk)
            if chunk != "[DONE]":
                accumulated += chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
    return {"id": f"ice-msg-{int(time.time())}", "type": "message", "role": "assistant", "model": request.model, "content": [{"type": "text", "text": accumulated}], "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": len(accumulated)//4}}

@app.post("/v1beta/models/{model}:streamGenerateContent")
async def gemini_stream_proxy(model: str, fastapi_request: Request, request: GeminiRequest, context: dict = Depends(verify_tenant)):
    ICE_TOTAL_QUERIES.inc() # Increment total queries for Prometheus
    adapter = get_provider_adapter(provider_hint="google")
    openai_msgs = []
    if request.systemInstruction and "parts" in request.systemInstruction:
        sys_mapped = adapter.map_multimodal_content(request.systemInstruction["parts"])
        if sys_mapped: openai_msgs.append({"role": "system", "content": sys_mapped})
    
    for c in request.contents:
        role = "assistant" if c.role == "model" else "user"
        parts_dicts = [p.model_dump(exclude_none=True) for p in c.parts]
        text_or_multimodal = adapter.map_multimodal_content(parts_dicts)
        if text_or_multimodal: openai_msgs.append({"role": role, "content": text_or_multimodal})
        
    temp = request.generationConfig.get("temperature", 0.7) if request.generationConfig else 0.7
    max_tokens = request.generationConfig.get("maxOutputTokens", 4096) if request.generationConfig else 4096

    async def gemini_stream_gen():
        async with track_concurrent_session(context["tenant_id"]):
            async for chunk in generate_ice_chunks(
                model, openai_msgs, temp, max_tokens, 
                context["tenant_id"], context["session_id"], context["user_id"], context["api_key"],
                options=request.options, tools=request.tools, tool_choice=request.toolConfig, # toolConfig is Gemini's tool_choice
                headers=fastapi_request.headers # Pass the request headers
            ):
                if chunk == "[DONE]":
                    break
                else:
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        gemini_chunk = {
                            "candidates": [{"content": {"parts": [{"text": delta}], "role": "model"}}],
                        }
                        if "x_ice_meta" in chunk:
                            gemini_chunk["x_ice_meta"] = chunk["x_ice_meta"]
                        yield f"data: {orjson.dumps(gemini_chunk).decode()}\n\n"
    return StreamingResponse(gemini_stream_gen(), media_type="text/event-stream")

@app.post("/v1beta/models/{model}:generateContent")
async def gemini_proxy(model: str, fastapi_request: Request, request: GeminiRequest, context: dict = Depends(verify_tenant)):
    ICE_TOTAL_QUERIES.inc() # Increment total queries for Prometheus
    adapter = get_provider_adapter(provider_hint="google")

    openai_msgs = []
    if request.systemInstruction and "parts" in request.systemInstruction:
        sys_mapped = adapter.map_multimodal_content(request.systemInstruction["parts"])
        if sys_mapped: openai_msgs.append({"role": "system", "content": sys_mapped})
        
    for c in request.contents:
        role = "assistant" if c.role == "model" else "user"
        parts_dicts = [p.model_dump(exclude_none=True) for p in c.parts]
        text_or_multimodal = adapter.map_multimodal_content(parts_dicts)
        if text_or_multimodal: openai_msgs.append({"role": role, "content": text_or_multimodal})
        
    temp = request.generationConfig.get("temperature", 0.7) if request.generationConfig else 0.7
    max_tokens = request.generationConfig.get("maxOutputTokens", 4096) if request.generationConfig else 4096

    accumulated = ""
    async with track_concurrent_session(context["tenant_id"]):
        async for chunk in generate_ice_chunks(
            model, openai_msgs, temp, max_tokens, 
            context["tenant_id"], context["session_id"], context["user_id"], context["api_key"],
            options=request.options, tools=request.tools, tool_choice=request.toolConfig, # toolConfig is Gemini's tool_choice
            headers=fastapi_request.headers # Pass the request headers
        ):
            if isinstance(chunk, dict) and "error" in chunk:
                return JSONResponse(status_code=502, content=chunk)
            if chunk != "[DONE]":
                accumulated += chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            
    return {
        "candidates": [{"content": {"parts": [{"text": accumulated}], "role": "model"}}],
        "usageMetadata": {"candidatesTokenCount": len(accumulated)//4, "totalTokenCount": len(accumulated)//4}
    }

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
Instrumentator().instrument(app).expose(app)

def start_server():
    """Starts the Uvicorn server for the FastAPI application."""
    import uvicorn
    uvicorn.run("ice.main:app", host="0.0.0.0", port=int(os.getenv("ICE_PORT", 8000)), reload=False, workers=int(os.getenv("ICE_WORKERS", "1")))

if __name__ == "__main__":
    start_server()
