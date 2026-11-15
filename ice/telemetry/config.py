# SPDX-License-Identifier: MIT

"""
ICE Remote Telemetry Configuration

Configuration for remote telemetry emission from ICE clients.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TelemetryConfig:
    """Configuration for remote telemetry emission."""

    # Core settings
    enabled: bool = True
    # Route SDK-client telemetry through the OTLP collector (gRPC/HTTP).
    # Mirrors the server-side OTEL_EXPORTER_OTLP_* contract — keeps one
    # ingestion pipe.
    endpoint: str = field(default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"))
    api_key: str = field(default_factory=lambda: os.getenv("ICE_TELEMETRY_API_KEY", ""))

    # Batching and flushing
    sampling_rate: float = 1.0
    batch_size: int = 50
    flush_interval: int = 15  # seconds
    max_queue_size: int = 10000
    timeout: int = 10  # seconds
    compression: str = "gzip"

    # Retry policy
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0  # seconds
    retry_max_delay: float = 30.0  # seconds

    # Privacy settings
    pii_redaction: bool = True
    hash_identifiers: bool = True
    allowed_attributes: List[str] = field(default_factory=lambda: ["service.name", "ice.version"])
    denied_attributes: List[str] = field(default_factory=lambda: [
        "user.email", "user.id", "api_key", "prompt", "completion",
        "authorization", "cookie", "x-api-key"
    ])
    anonymize_ips: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.sampling_rate < 0 or self.sampling_rate > 1:
            raise ValueError("sampling_rate must be between 0 and 1")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.flush_interval <= 0:
            raise ValueError("flush_interval must be positive")
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.compression not in ("gzip", "none"):
            raise ValueError("compression must be 'gzip' or 'none'")
        if self.retry_max_attempts < 0:
            raise ValueError("retry_max_attempts must be non-negative")
        if self.retry_base_delay <= 0:
            raise ValueError("retry_base_delay must be positive")
        if self.retry_max_delay <= 0:
            raise ValueError("retry_max_delay must be positive")