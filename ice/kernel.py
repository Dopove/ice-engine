# SPDX-License-Identifier: MIT

# ice/kernel.py
import os
import asyncpg
import redis.asyncio as redis
from .core.security import SecurityManager
from .core.episodic import EpisodicManager
from .core.reasoning import ReasoningManager
from .core.pager import ContextPager, EmbeddingModel
from .core.ingestion import IngestionPipeline # Added this import
from .telemetry import TelemetryConfig, RemoteTelemetryClient

class ICEKernel:
    def __init__(self, license_key: str = None, db_url: str = None, redis_url: str = None, **kwargs):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.db_pool = None
        self.redis_pool = None

        # 1. Security Handshake
        self.security = SecurityManager()
        self.security.verify_or_exit()

        # 2. Core Managers
        self.embedder = EmbeddingModel()

        self.pager = ContextPager(self.embedder, **kwargs)
        self.episodic = EpisodicManager(self.db_pool, self.redis_pool)
        self.reasoning = ReasoningManager(self.db_pool, self.redis_pool)
        self.ingestion = IngestionPipeline(self.episodic, self.embedder) # Pass embedder

        # 3. Telemetry
        self.telemetry_config = TelemetryConfig(
            endpoint=kwargs.get("telemetry_endpoint", os.getenv("ICE_TELEMETRY_ENDPOINT")),
            api_key=kwargs.get("telemetry_api_key", os.getenv("ICE_TELEMETRY_API_KEY")),
            enabled=kwargs.get("telemetry_enabled", os.getenv("ICE_TELEMETRY_ENABLED", "true").lower() == "true"),
        )
        self.telemetry = RemoteTelemetryClient(self.telemetry_config)

        # Store all kwargs to make them available globally
        self.config = kwargs

    async def connect(self):
        """Connects to the database and redis pools."""
        if os.getenv("ICE_SKIP_INFRA_CONNECT") == "1":
            print("[System]: Skipping Infrastructure Connection (Mock/Demo Mode Active).")
            return

        if self.db_url:
            from .setup_db import ensure_postgres_available
            auto_provision = os.getenv("ICE_AUTO_PROVISION_DB", "1") == "1"
            if not await ensure_postgres_available(self.db_url, auto_provision=auto_provision):
                raise RuntimeError(f"Postgres unavailable at {self.db_url}")
            self.db_pool = await asyncpg.create_pool(dsn=self.db_url)
            self.episodic.db_pool = self.db_pool
            self.reasoning.db_pool = self.db_pool
            self.security.db_pool = self.db_pool
            await self.security.register_node()
        if self.redis_url:
            self.redis_pool = redis.from_url(self.redis_url)
            self.episodic.redis = self.redis_pool
            self.reasoning.redis = self.redis_pool

        # Start telemetry client
        await self.telemetry.start()

    async def disconnect(self):
        """Closes connection pools."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_pool:
            await self.redis_pool.close()
        # Stop telemetry client
        await self.telemetry.stop()

    async def health(self):
        """Returns the health of the kernel's connections."""
        db_status = "connected" if self.db_pool else "disconnected"
        redis_status = "connected" if self.redis_pool else "disconnected"
        return {"database": db_status, "redis": redis_status}
