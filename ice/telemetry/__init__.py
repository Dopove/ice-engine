# SPDX-License-Identifier: BSL-1.1

"""
ICE Remote Telemetry SDK Module

Provides client-side telemetry emission for distributed ICE deployments.
"""

from .config import TelemetryConfig
from .emitter import RemoteTelemetryClient
from .privacy import hash_identifier, redact_pii

__all__ = [
    "TelemetryConfig",
    "RemoteTelemetryClient",
    "hash_identifier",
    "redact_pii",
]