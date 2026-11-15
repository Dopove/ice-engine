# SPDX-License-Identifier: MIT

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    ICE_PORT: int = 8000
    ICE_SKU: str = "ICE-ENTERPRISE"
    ICE_MODE: str = "production"
    ICE_LOG_LEVEL: str = "INFO"
    
    # Redis Settings
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Infrastructure Settings
    ICE_SKIP_INFRA_CONNECT: int = 0
    ICE_MAX_STITCH_CONCURRENCY: int = 10
    ICE_MAX_INGESTION_CONCURRENCY: int = 5
    ICE_CHUNK_SIZE: int = 8000
    ICE_CHUNK_OVERLAP: int = 500
    
    # Observability
    ICE_ENABLE_TRACING: int = 0
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    
    # Compliance Security
    ICE_RAG_ENABLE_COMPLIANCE: str = "false"
    ICE_RAG_COMPLIANCE_LEVEL: str = "standard"
    ICE_RAG_CONFIG_FILE: Optional[str] = None
    ICE_RAG_PARSER: str = "docling"
    ICE_RAG_ENABLE_IMAGES: str = "true"
    ICE_RAG_ENABLE_TABLES: str = "true"
    ICE_RAG_ENABLE_EQUATIONS: str = "true"
    ICE_PURGE_WEBHOOK_URL: Optional[str] = None
    ICE_PRE_PURGE_WEBHOOK_URL: Optional[str] = None
    ICE_ALLOW_DEFAULT_KEY: int = 0
    ICE_LICENSE_JWT: Optional[str] = None
    ICE_PEER_NODES: Optional[str] = None
    ICE_INTERNAL_API_KEY: Optional[str] = None

    # Worker Settings
    ICE_USE_ARQ: int = 1

    # Diagnostics Telemetry
    ICE_CRASH_REPORT_URL: Optional[str] = "https://diagnostics.ice-engine.com/v1/reports"
    ICE_ENABLE_CRASH_REPORTING: int = 1
    # No default: unlike old hardcoded "client-dashboard-secret-123",
    # unset means telemetry endpoint fails closed (rejects everything)
    # instead guessable reading source file.
    ICE_TELEMETRY_VIEW_SECRET: Optional[str] = None

    # AWS License Manager (Enterprise Only)
    ICE_AWS_LICENSE_ARN: Optional[str] = None
    ICE_LICENSE_PATH: str = ".ice-license"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
