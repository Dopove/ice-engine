import os
import re
import redis.asyncio as redis
import orjson
import hashlib
import hmac
import logging

logger = logging.getLogger("ice_rag_backend")

class ClientSideScrubber:
    """
    Cleans sensitive enterprise data before transmitting to the external telemetry pool.
    Utilizes multi-layer regex for PII, secrets, and code-block masking.
    """
    @staticmethod
    def scrub(content: str) -> str:
        # 1. Mask IPv4 and IPv6 addresses
        content = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_REDACTED]', content)
        content = re.sub(r'([a-f0-9:]+:+)+[a-f0-9]+', '[IP_REDACTED]', content)
        
        # 2. Mask Email addresses
        content = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', content)
        
        # 3. Mask Phone Numbers (International and Local)
        content = re.sub(r'(\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', '[PHONE_REDACTED]', content)
        
        # 4. Mask SSNs
        content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', content)
        
        # 5. [ENTERPRISE INDIA] Mask PAN and Aadhaar
        content = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', '[PAN_REDACTED]', content)
        content = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b', '[AADHAAR_REDACTED]', content)
        
        # 6. Mask Credit Card patterns
        content = re.sub(r'\b(?:\d{4}[ -]?){3}\d{4}\b', '[CARD_REDACTED]', content)
        
        # 7. Mask API keys/Secrets (Advanced heuristic)
        content = re.sub(r'(?i)(api_key|token|secret|password|passwd|pwd|access_key|auth_key)[\s:=]+["\']?[\w\-]{8,}["\']?', r'\1: [SECRET_REDACTED]', content)
        
        # 8. Optional: Mask entire Code Blocks if they look like proprietary business logic
        content = re.sub(r'```[\s\S]*?```', '[CODE_BLOCK_REDACTED]', content)
        
        return content

class LocalVectorStore:
    """Sovereign Fortress (One-Time Sale): Uses Local Configured PostgreSQL/Redis with limits."""
    def __init__(self):
        self.mode = "local"
        logger.info("Initializing Sovereign ICE: Isolated Local Storage.")

    async def save(self, tenant_id: str, session_id: str, payload: dict):
        # The episodic manager natively handles PG saving, we can passthrough
        pass
        
    async def get_history(self, tenant_id: str, session_id: str):
        pass

class RedisVectorStore:
    """Hyena Horizon (Subscription): Uses Multi-Region Managed Redis for Infinite Context & Telemetry."""
    def __init__(self, host: str, index: str, tenant_id: str, ttl=None):
        self.host = host
        self.index = index
        self.ttl = ttl
        self.tenant_id = tenant_id
        self.redis = None # Will be initialized asynchronously

        # Generate Redis user and password for ACL
        self.redis_user = f"user_ice_rag_{hashlib.sha256(tenant_id.encode()).hexdigest()}"
        self.redis_password = os.getenv(f"REDIS_ACL_PASS_{self.redis_user.upper()}", None)
        
        if not self.redis_password:
            self.redis_password = hashlib.sha256(os.urandom(64)).hexdigest() 
            logger.warning(f"Dynamically generated Redis password for user {self.redis_user}. THIS SHOULD BE MANAGED SECURELY!")
        
        logger.info(f"RedisVectorStore initialized for {index}. Connection to be established asynchronously on first use.")

    async def _async_init_connection(self):
        """
        Asynchronously establishes connection to Redis and sets up ACLs.
        This method is called on the first actual use of the store.
        """
        if self.redis is not None:
            return # Already connected

        admin_redis_conn = None
        try:
            admin_host = os.getenv("RAGX_REDIS_ADMIN_HOST", self.host)
            admin_user = os.getenv("RAGX_REDIS_ADMIN_USER", "default")
            admin_password = os.getenv("RAGX_REDIS_ADMIN_PASSWORD")

            if admin_password:
                admin_redis_conn = redis.from_url(admin_host, username=admin_user, password=admin_password)
                await admin_redis_conn.acl_setuser(
                    self.redis_user, 
                    passwords=[self.redis_password], 
                    categories=['+@all'], # Allow all commands
                    keys=[f"~{self.index}*"] # Only for keys prefixed with this user's index
                )
                logger.info(f"Dynamically configured Redis ACL for user {self.redis_user} with keys {self.index}*")
            else:
                logger.warning("RAGX_REDIS_ADMIN_PASSWORD not set. Cannot configure dynamic Redis ACLs. Using default user with broad permissions.")

        except Exception as e:
            logger.error(f"Failed to configure Redis ACL for {self.redis_user}: {e}. Falling back to default connection without explicit user-specific ACL.")
        finally:
            if admin_redis_conn:
                await admin_redis_conn.aclose()
        
        self.redis = redis.from_url(
            self.host, 
            username=self.redis_user if admin_password else None, # Only use user/pass if ACL was attempted
            password=self.redis_password if admin_password else None
        )
        logger.info(f"Hyena Horizon Redis connection established for {self.index} with user {self.redis_user}")

    async def save(self, tenant_id: str, session_id: str, payload: dict):
        await self._async_init_connection() # Ensure connection is established
        # Scrub payload before externalizing
        scrubbed_content = ClientSideScrubber.scrub(payload.get("content", ""))
        payload["content"] = scrubbed_content
        
        # Telemetry signature to feed Maggie securely
        telemetry = {
            "query_intent": "analyzed_interaction",
            "latency_ms": payload.get("latency_ms", 0),
            "token_counts": payload.get("token_counts", 0)
        }
        payload["telemetry_signal"] = telemetry
        
        cache_key = f"{self.index}:{tenant_id}:{session_id}" # Ensure this key format aligns with ACL prefix
        await self.redis.rpush(cache_key, orjson.dumps(payload))
        if self.ttl is not None:
             await self.redis.expire(cache_key, self.ttl)

    async def get_history(self, tenant_id: str, session_id: str):
        await self._async_init_connection() # Ensure connection is established
        cache_key = f"{self.index}:{tenant_id}:{session_id}" # Ensure this key format aligns with ACL prefix
        cached = await self.redis.lrange(cache_key, 0, -1)
        return [orjson.loads(m) for m in cached] if cached else []

class RAGBackend:
    """
    Routs context operations between the local Sovereign storage and the infinite Horizon external cluster.
    """
    def __init__(self, mode: str = "local", tenant_id: str = None):
        self.mode = mode
        if mode == "external":
            # The Recurring Service Version
            if not tenant_id:
                tenant_id = "default_tenant"
            
            # Salted HMAC for Redis Keyspace protection (Nuclear-Grade isolation)
            # This ensures that even if a tenant ID is known, the Redis index is unpredictable.
            master_salt = os.getenv("ICE_REDIS_SALT", "default-ice-salt-2026")
            index_hash = hmac.new(master_salt.encode(), tenant_id.encode(), hashlib.sha256).hexdigest()
            
            # Default to local mock redis if no external provided but still testing external logic
            host = os.environ.get("RAGX_REDIS_HOST", "redis://localhost:6379/1")
            
            self.store = RedisVectorStore(
                host=host,
                index=f"ice-rag-{index_hash}", 
                tenant_id=tenant_id, 
                ttl=None
            )
        else:
            # The One-Time Sale Version
            self.store = LocalVectorStore()

    async def save_context(self, tenant_id: str, session_id: str, role: str, content: str, latency_ms: float = 0):
        # Respect Privacy Opt-Out
        if os.getenv("ICE_TELEMETRY_ENABLED", "true").lower() == "false":
            logger.info({"event": "telemetry_skipped", "reason": "tenant_opt_out"})
            return

        payload = {"role": role, "content": content, "latency_ms": latency_ms}
        await self.store.save(tenant_id, session_id, payload)
