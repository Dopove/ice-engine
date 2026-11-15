# SPDX-License-Identifier: BSL-1.1

"""
ICE Telemetry Middleware

FastAPI middleware for automatic telemetry collection.
"""

import time
import logging
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .emitter import RemoteTelemetryClient
from .config import TelemetryConfig

logger = logging.getLogger("ice_telemetry")


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic HTTP request/response telemetry.

    Collects:
    - Request latency
    - HTTP status codes
    - Request/response sizes
    - Error rates
    """

    def __init__(
        self,
        app: ASGIApp,
        telemetry_client: Optional[RemoteTelemetryClient] = None,
        config: Optional[TelemetryConfig] = None,
        excluded_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.telemetry_client = telemetry_client
        self.config = config or TelemetryConfig()
        self.excluded_paths = excluded_paths or ["/health", "/live", "/ready", "/metrics", "/v1/telemetry"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skip if telemetry not enabled
        if not self.config.enabled or not self.telemetry_client:
            return await call_next(request)

        start_time = time.time()
        request_size = 0

        # Calculate request size
        if hasattr(request, "body"):
            try:
                body = await request.body()
                request_size = len(body)
                # Re-create request with body for downstream
                request._body = body
            except Exception:
                pass

        # Extract tenant info from headers
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("x-ice-tenant-id")
        session_id = request.headers.get("x-session-id") or request.headers.get("x-ice-session-id")

        try:
            response = await call_next(request)
        except Exception as e:
            # Record error telemetry
            await self._emit_error_telemetry(
                request, tenant_id, session_id, time.time() - start_time, str(e)
            )
            raise

        duration = time.time() - start_time
        response_size = len(response.body) if hasattr(response, "body") else 0

        # Emit request telemetry
        await self._emit_request_telemetry(
            request=request,
            response=response,
            tenant_id=tenant_id,
            session_id=session_id,
            duration=duration,
            request_size=request_size,
            response_size=response_size,
        )

        return response

    async def _emit_request_telemetry(
        self,
        request: Request,
        response: Response,
        tenant_id: Optional[str],
        session_id: Optional[str],
        duration: float,
        request_size: int,
        response_size: int,
    ):
        """Emit HTTP request/response telemetry."""
        if not self.telemetry_client or not self.config.enabled:
            return

        payload = {
            "type": "http_request",
            "timestamp": time.time(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "request_size_bytes": request_size,
            "response_size_bytes": response_size,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "user_agent": request.headers.get("user-agent", ""),
        }

        try:
            await self.telemetry_client.emit(payload)
        except Exception as e:
            # Don't let telemetry errors affect the request
            pass

    async def _emit_error_telemetry(
        self,
        request: Request,
        tenant_id: Optional[str],
        session_id: Optional[str],
        duration: float,
        error: str,
    ):
        """Emit error telemetry for failed requests."""
        if not self.telemetry_client or not self.config.enabled:
            return

        payload = {
            "type": "http_error",
            "timestamp": time.time(),
            "method": request.method,
            "path": request.url.path,
            "error": error,
            "duration_ms": duration * 1000,
            "tenant_id": tenant_id,
            "session_id": session_id,
        }

        try:
            await self.telemetry_client.emit(payload)
        except Exception:
            pass


def create_telemetry_middleware(
    app: ASGIApp,
    telemetry_client: Optional[RemoteTelemetryClient] = None,
    config: Optional[TelemetryConfig] = None,
) -> TelemetryMiddleware:
    """Factory function to create telemetry middleware."""
    return TelemetryMiddleware(app, telemetry_client, config)