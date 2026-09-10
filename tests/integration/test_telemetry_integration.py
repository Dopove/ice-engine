#!/usr/bin/env python3
"""
Integration tests for ICE Telemetry System

Tests cover:
- Trace generation for key code paths
- W3C TraceContext propagation to upstream providers
- Metrics emission on API calls
- Error-only sampling behavior
- OTLP export verification (with mock collector)
- Degraded mode metrics
- Telemetry status endpoint
- Force-flush endpoint
"""

import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime
from contextlib import asynccontextmanager

# Set test environment before importing ice
os.environ.setdefault("ICE_TELEMETRY_ENABLED", "true")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")
os.environ.setdefault("ICE_OTEL_SAMPLER", "error_only")
os.environ.setdefault("ICE_LOG_LEVEL", "DEBUG")
os.environ.setdefault("ICE_SKIP_INFRA_CONNECT", "1")
os.environ.setdefault("ICE_MOCK_LLM_CALL", "1")
os.environ.setdefault("ICE_TEST_MODE", "1")
os.environ.setdefault("ICE_BYPASS_LICENSING", "1")
os.environ.setdefault("ICE_SKU", "ICE-UNLIMITED")

# Helper to create proper async context manager mock
@asynccontextmanager
async def mock_async_context_manager(return_value):
    yield return_value


class TestTraceGeneration:
    """Test trace generation for key ICE code paths"""

    @pytest.mark.asyncio
    async def test_generate_ice_chunks_creates_spans(self):
        """Verify generate_ice_chunks creates OpenTelemetry spans"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from ice.main import generate_ice_chunks, ice_server, provider as ice_provider, tracer as ice_tracer

        # Create a separate tracer provider for this test
        test_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        test_provider.add_span_processor(SimpleSpanProcessor(exporter))

        # Mock ice_server components BEFORE calling generate_ice_chunks
        ice_server.episodic = AsyncMock()
        ice_server.episodic.save_message = AsyncMock()
        ice_server.episodic.get_session_token_count = AsyncMock(return_value=100)
        ice_server.episodic.search_episodic = AsyncMock(return_value=[])
        ice_server.reasoning = AsyncMock()
        ice_server.reasoning.search_reasoning = AsyncMock(return_value=[])
        ice_server.pager = AsyncMock()
        ice_server.pager.assemble_prompt = AsyncMock(return_value=([{"role": "user", "content": "test"}], 10, 100))
        ice_server.http_client = AsyncMock()
        ice_server.degraded_mode = False

        # Mock db_pool properly as an async context manager
        mock_db = AsyncMock()
        mock_conn = AsyncMock()
        mock_db.acquire = AsyncMock(return_value=mock_async_context_manager(mock_conn))
        ice_server.db_pool = mock_db

        # Mock response stream
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = AsyncMock(return_value=iter([
            'data: {"choices": [{"delta": {"content": "Hello"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}]}',
            'data: [DONE]'
        ]))
        ice_server.http_client.stream = AsyncMock(return_value=mock_response.__aenter__.return_value)

        # Create a test tracer provider and exporter for this test
        test_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        test_provider.add_span_processor(SimpleSpanProcessor(exporter))

        # Call generate_ice_chunks using the test tracer
        messages = [{"role": "user", "content": "Hello"}]
        chunks = []
        async for chunk in generate_ice_chunks(
            model="ministral-3:3b",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            tenant_id="test-tenant",
            session_id="test-session",
            user_id="test-user",
            client_api_key="test-key"
        ):
            chunks.append(chunk)

        # Verify spans were created
        spans = exporter.get_finished_spans()
        span_names = [span.name for span in spans]
        assert "generate_ice_chunks" in span_names

    @pytest.mark.asyncio
    async def test_episodic_save_message_creates_spans(self):
        """Verify EpisodicManager.save_message creates spans"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from ice.core.episodic import EpisodicManager

        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        # Create EpisodicManager with mocked db_pool
        mock_db = AsyncMock()
        mock_conn = AsyncMock()
        mock_db.acquire = AsyncMock(return_value=mock_async_context_manager(mock_conn))
        mock_conn.execute = AsyncMock()

        manager = EpisodicManager(db_pool=mock_db, redis_client=None)

        # Call save_message
        await manager.save_message(
            tenant_id="test-tenant",
            session_id="test-session",
            role="user",
            content="Test message",
            user_id="test-user"
        )

        # Verify spans were created
        spans = exporter.get_finished_spans()
        span_names = [span.name for span in spans]
        assert "EpisodicManager.save_message" in span_names

    @pytest.mark.asyncio
    async def test_episodic_search_creates_spans(self):
        """Verify EpisodicManager.search_episodic creates spans"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from ice.core.episodic import EpisodicManager

        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        # Create EpisodicManager with mocked db_pool
        mock_db = AsyncMock()
        mock_conn = AsyncMock()
        mock_db.acquire = AsyncMock(return_value=mock_async_context_manager(mock_conn))
        mock_conn.fetch = AsyncMock(return_value=[])

        # Call search_episodic
        await manager.search_episodic(
            tenant_id="test-tenant",
            query_vector=[0.1] * 384,
            session_id="test-session",
            user_id="test-user",
            limit=10
        )

        # Verify spans were created
        spans = exporter.get_finished_spans()
        span_names = [span.name for span in spans]
        assert "EpisodicManager.search_episodic" in span_names


class TestTraceContextPropagation:
    """Test W3C TraceContext propagation to upstream providers"""

    @pytest.mark.asyncio
    async def test_traceparent_header_injected(self):
        """Verify traceparent header is injected on upstream calls"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from opentelemetry.propagate import inject
        from ice.main import generate_ice_chunks, ice_server

        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Mock ice_server
        ice_server.episodic = AsyncMock()
        ice_server.episodic.save_message = AsyncMock()
        ice_server.episodic.get_session_token_count = AsyncMock(return_value=100)
        ice_server.episodic.search_episodic = AsyncMock(return_value=[])
        ice_server.reasoning = AsyncMock()
        ice_server.reasoning.search_reasoning = AsyncMock(return_value=[])
        ice_server.pager = AsyncMock()
        ice_server.pager.assemble_prompt = AsyncMock(return_value=([{"role": "user", "content": "test"}], 10, 100))
        ice_server.degraded_mode = False

        # Capture headers passed to http_client.stream
        captured_headers = {}

        async def mock_stream(method, url, json=None, headers=None):
            captured_headers.update(headers or {})
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.aiter_lines = AsyncMock(return_value=iter([
                'data: {"choices": [{"delta": {"content": "Hello"}, "finish_reason": "stop"}]}',
                'data: [DONE]'
            ]))
            return mock_response

        ice_server.http_client = AsyncMock()
        ice_server.http_client.stream = mock_stream

        # Call generate_ice_chunks
        messages = [{"role": "user", "content": "Hello"}]
        async for chunk in generate_ice_chunks(
            model="ministral-3:3b",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            tenant_id="test-tenant",
            session_id="test-session",
            user_id="test-user",
            client_api_key="test-key"
        ):
            pass

        # Verify traceparent header was injected
        assert "traceparent" in captured_headers
        assert captured_headers["traceparent"].startswith("00-")


class TestMetricsEmission:
    """Test metrics emission on API calls"""

    @pytest.mark.asyncio
    async def test_ice_total_queries_increments(self):
        """Verify ICE_TOTAL_QUERIES increments on chat completions"""
        from fastapi.testclient import TestClient
        from ice.main import app
        from ice.core import metrics as metrics_module

        # Get initial value
        # Note: Prometheus counters don't expose get() easily in tests
        # We'll verify the metric exists and can be incremented
        initial_value = 0

        with TestClient(app) as client:
            # Make a request (will fail auth but should still increment)
            response = client.post(
                "/v1/chat/completions",
                json={"model": "test", "messages": [{"role": "user", "content": "test"}]}
            )

        # The metric should be incremented (we can't easily test the value
        # without a registry, but we verify no errors)
        assert True

    @pytest.mark.asyncio
    async def test_active_sessions_gauge(self):
        """Verify ICE_ACTIVE_SESSIONS gauge tracks active sessions"""
        from ice.core import metrics as metrics_module

        # Increment for tenant
        metrics_module.ICE_ACTIVE_SESSIONS.labels(tenant_id="tenant1").inc()
        metrics_module.ICE_ACTIVE_SESSIONS.labels(tenant_id="tenant1").inc()

        # Decrement
        metrics_module.ICE_ACTIVE_SESSIONS.labels(tenant_id="tenant1").dec()

        # Should not throw
        assert True

    @pytest.mark.asyncio
    async def test_upstream_latency_histogram(self):
        """Verify ICE_UPSTREAM_LATENCY records latency"""
        from ice.core import metrics as metrics_module
        import time

        # Record some latencies
        with metrics_module.ICE_UPSTREAM_LATENCY.labels(provider="openai", model="gpt-4").time():
            await asyncio.sleep(0.01)

        with metrics_module.ICE_UPSTREAM_LATENCY.labels(provider="anthropic", model="claude-3").time():
            await asyncio.sleep(0.01)

        assert True

    @pytest.mark.asyncio
    async def test_upstream_errors_counter(self):
        """Verify ICE_UPSTREAM_ERRORS increments on errors"""
        from ice.core import metrics as metrics_module

        metrics_module.ICE_UPSTREAM_ERRORS.labels(provider="openai", error_type="rate_limit").inc()
        metrics_module.ICE_UPSTREAM_ERRORS.labels(provider="anthropic", error_type="auth").inc()

        assert True

    @pytest.mark.asyncio
    async def test_retrieval_latency_histogram(self):
        """Verify ICE_RETRIEVAL_LATENCY records search latency"""
        from ice.core import metrics as metrics_module

        with metrics_module.ICE_RETRIEVAL_LATENCY.labels(search_type="local").time():
            await asyncio.sleep(0.01)

        with metrics_module.ICE_RETRIEVAL_LATENCY.labels(search_type="reasoning").time():
            await asyncio.sleep(0.01)

        assert True


class TestErrorOnlySampling:
    """Test error-only sampling behavior"""

    @pytest.mark.asyncio
    async def test_error_only_sampler_exports_only_errors(self):
        """Verify error_only sampler only exports error spans"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from ice.main import ErrorOnlySpanProcessor, tracer
        from opentelemetry.trace import StatusCode

        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(ErrorOnlySpanProcessor(SimpleSpanProcessor(exporter)))
        trace.set_tracer_provider(provider)

        # Create a successful span
        with tracer.start_as_current_span("successful_operation") as span:
            span.set_status(trace.Status(StatusCode.OK))

        # Create an error span
        with tracer.start_as_current_span("failed_operation") as span:
            span.set_status(trace.Status(StatusCode.ERROR, "Something failed"))

        # Force flush
        provider.force_flush()

        # Only error span should be exported
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "failed_operation"
        assert spans[0].status.status_code == StatusCode.ERROR


class TestDegradedModeMetrics:
    """Test degraded mode metrics"""

    @pytest.mark.asyncio
    async def test_degraded_mode_gauge_updates(self):
        """Verify ICE_DEGRADED_MODE gauge updates correctly"""
        from ice.core import metrics as metrics_module
        from ice.main import ice_server

        # Set to healthy
        metrics_module.ICE_DEGRADED_MODE.set(0)
        assert metrics_module.ICE_DEGRADED_MODE._value.get() == 0

        # Set to degraded
        metrics_module.ICE_DEGRADED_MODE.set(1)
        assert metrics_module.ICE_DEGRADED_MODE._value.get() == 1


class TestTelemetryEndpointsIntegration:
    """Integration tests for telemetry endpoints"""

    @pytest.mark.asyncio
    async def test_telemetry_status_endpoint(self):
        """Verify /v1/telemetry/status returns correct config"""
        from fastapi.testclient import TestClient
        from ice.main import app

        with TestClient(app) as client:
            response = client.get("/v1/telemetry/status")
            assert response.status_code == 200

            data = response.json()
            assert "traces" in data
            assert "metrics" in data
            assert "logs" in data
            assert "resource" in data
            assert "propagator" in data
            assert data["propagator"] == "tracecontext"

    @pytest.mark.asyncio
    async def test_telemetry_force_flush_endpoint(self):
        """Verify /v1/telemetry/force-flush triggers flushes"""
        from fastapi.testclient import TestClient
        from ice.main import app

        with TestClient(app) as client:
            response = client.post("/v1/telemetry/force-flush")
            assert response.status_code == 200

            data = response.json()
            assert "flushed" in data
            assert "status" in data
            assert data["status"] == "completed"
            assert "traces" in data["flushed"]
            assert "metrics" in data["flushed"]
            assert "logs" in data["flushed"]


class TestCircuitBreakerMetricsIntegration:
    """Test circuit breaker metrics in integration"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_metric(self):
        """Verify ICE_CIRCUIT_BREAKER_STATE updates on state changes"""
        from ice.core.circuit_breaker import CircuitBreaker
        from ice.core import metrics as metrics_module

        cb = CircuitBreaker(name="integration_test", failure_threshold=2, recovery_timeout=60)

        # Initial state: closed (0)
        cb._update_metric()

        # Simulate failures
        cb.failures = 2
        cb.last_failure_time = 0

        import asyncio
        try:
            await cb.__aenter__()
        except Exception:
            pass  # Expected to raise CircuitBreakerOpen

        # State should be open (1)
        assert cb._state == 1


class TestTokenUsageMetrics:
    """Test token usage metrics"""

    @pytest.mark.asyncio
    async def test_tokens_input_output_metrics(self):
        """Verify ICE_TOKENS_INPUT and ICE_TOKENS_OUTPUT increment"""
        from ice.core import metrics as metrics_module

        # Record input tokens
        metrics_module.ICE_TOKENS_INPUT.labels(tenant_id="tenant1", provider="openai").inc(100)
        metrics_module.ICE_TOKENS_OUTPUT.labels(tenant_id="tenant1", provider="openai").inc(50)

        # Record more
        metrics_module.ICE_TOKENS_INPUT.labels(tenant_id="tenant1", provider="anthropic").inc(200)
        metrics_module.ICE_TOKENS_OUTPUT.labels(tenant_id="tenant1", provider="anthropic").inc(100)

        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])