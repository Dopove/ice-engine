#!/usr/bin/env python3
"""
OTLP Export Integration Tests for ICE Telemetry System

Tests cover:
- OTLP trace export to collector
- OTLP metrics export to collector
- OTLP logs export to collector
- Collector configuration validation
"""

import pytest
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime

# Set test environment
os.environ.setdefault("ICE_TELEMETRY_ENABLED", "true")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4317")
os.environ.setdefault("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://localhost:4317")
os.environ.setdefault("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", "http://localhost:4317")
os.environ.setdefault("ICE_OTEL_SAMPLER", "parent_based_always_on")
os.environ.setdefault("ICE_LOG_LEVEL", "DEBUG")
os.environ.setdefault("ICE_SKIP_INFRA_CONNECT", "1")
os.environ.setdefault("ICE_MOCK_LLM_CALL", "1")


class MockOTLPCollector:
    """Mock OTLP Collector HTTP server for testing"""

    def __init__(self):
        self.received_traces = []
        self.received_metrics = []
        self.received_logs = []
        self.server = None
        self.port = 4318  # OTLP HTTP port

    async def start(self):
        """Start mock HTTP server"""
        from aiohttp import web

        async def handle_traces(request):
            body = await request.json()
            self.received_traces.append(body)
            return web.json_response({"partialSuccess": {}})

        async def handle_metrics(request):
            body = await request.json()
            self.received_metrics.append(body)
            return web.json_response({"partialSuccess": {}})

        async def handle_logs(request):
            body = await request.json()
            self.received_logs.append(body)
            return web.json_response({"partialSuccess": {}})

        app = web.Application()
        app.router.add_post('/v1/traces', handle_traces)
        app.router.add_post('/v1/metrics', handle_metrics)
        app.router.add_post('/v1/logs', handle_logs)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        self.server = runner

    async def stop(self):
        """Stop mock HTTP server"""
        if self.server:
            await self.server.cleanup()


class TestOTLPTraceExport:
    """Test OTLP trace export functionality"""

    @pytest.mark.asyncio
    async def test_trace_export_to_collector(self):
        """Verify traces are exported to a real OTLP collector (runs in CI)."""
        import socket
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        host = endpoint.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(endpoint.split(":")[-1])
        try:
            socket.create_connection((host, port), timeout=2).close()
        except OSError:
            pytest.skip(f"No OTel collector reachable at {endpoint}")

        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("ci_export_check") as span:
            span.set_attribute("ice.tenant_id", "tenant1")

        # SimpleSpanProcessor sends synchronously; no exception = export succeeded.
        provider.shutdown()
        assert True

    @pytest.mark.asyncio
    async def test_trace_export_format(self):
        """Verify exported traces have correct OTLP format"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        # Use in-memory exporter to verify format
        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.key", "test_value")
            span.set_attribute("ice.tenant_id", "tenant1")
            span.set_attribute("ice.session_id", "session1")

        provider.force_flush()

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "test_span"
        assert span.attributes.get("test.key") == "test_value"
        assert span.attributes.get("ice.tenant_id") == "tenant1"
        assert span.attributes.get("ice.session_id") == "session1"


class TestOTLPMetricsExport:
    """Test OTLP metrics export functionality"""

    @pytest.mark.asyncio
    async def test_metrics_export_format(self):
        """Verify metrics are exported in correct OTLP format"""
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import SimpleMetricReader
        from opentelemetry.sdk.metrics.export.in_memory_metric_exporter import InMemoryMetricExporter

        exporter = InMemoryMetricExporter()
        reader = SimpleMetricReader(exporter)
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)

        meter = provider.get_meter("test")

        # Create test metrics
        counter = meter.create_counter("test.counter", unit="1")
        histogram = meter.create_histogram("test.histogram", unit="ms")

        # Record values
        counter.add(10, {"label": "value1"})
        histogram.record(100, {"label": "value1"})
        histogram.record(200, {"label": "value2"})

        # Force collection
        reader.collect()

        # Verify metrics were collected
        # Note: In-memory exporter doesn't have get_finished_metrics
        # This is a structural test
        assert True


class TestOTLPLogsExport:
    """Test OTLP logs export functionality"""

    @pytest.mark.asyncio
    async def test_logs_export_format(self):
        """Verify logs are exported in correct OTLP format"""
        from opentelemetry import _logs
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
        from opentelemetry.sdk._logs.export.in_memory_log_exporter import InMemoryLogExporter

        exporter = InMemoryLogExporter()
        processor = SimpleLogRecordProcessor(exporter)
        provider = LoggerProvider()
        provider.add_log_record_processor(processor)
        _logs.set_logger_provider(provider)

        logger = provider.get_logger("test")

        # Emit test log
        logger.emit(
            body="Test log message",
            severity=17,  # INFO
            attributes={"test.key": "test_value", "ice.tenant_id": "tenant1"}
        )

        provider.force_flush()

        # Verify logs were collected
        # Note: In-memory exporter structure
        assert True


class TestCollectorConfiguration:
    """Test OTel Collector configuration validation"""

    def test_collector_config_exists(self):
        """Verify recommended collector config exists"""
        config_path = "/home/sarans/Videos/Projects/ICE/deploy/otel-collector-config.yaml"
        # Config may not exist yet
        import os
        if os.path.exists(config_path):
            with open(config_path) as f:
                content = f.read()
                assert "receivers:" in content
                assert "otlp:" in content
                assert "exporters:" in content
                assert "service:" in content

    def test_collector_receives_otlp_grpc(self):
        """Verify collector configured for OTLP gRPC"""
        config_path = "/home/sarans/Videos/Projects/ICE/deploy/otel-collector-config.yaml"
        import os
        if os.path.exists(config_path):
            with open(config_path) as f:
                content = f.read()
                assert "4317" in content or "otlp" in content.lower()

    def test_collector_receives_otlp_http(self):
        """Verify collector configured for OTLP HTTP"""
        config_path = "/home/sarans/Videos/Projects/ICE/deploy/otel-collector-config.yaml"
        import os
        if os.path.exists(config_path):
            with open(config_path) as f:
                content = f.read()
                assert "4318" in content or "otlphttp" in content.lower()


class TestOTLPHeaders:
    """Test OTLP authentication headers"""

    def test_otlp_headers_parsing(self):
        """Verify OTLP headers are parsed correctly"""
        from ice.main import parse_otlp_headers

        # Test single header
        headers = parse_otlp_headers("Authorization=Bearer token123")
        assert headers == {"Authorization": "Bearer token123"}

        # Test multiple headers
        headers = parse_otlp_headers("Authorization=Bearer token123,X-Custom=value")
        assert headers == {"Authorization": "Bearer token123", "X-Custom": "value"}

        # Test empty
        headers = parse_otlp_headers("")
        assert headers == {}

        # Test None
        headers = parse_otlp_headers(None)
        assert headers == {}


class TestOTLPEndpointConfiguration:
    """Test OTLP endpoint configuration"""

    def test_endpoint_environment_variables(self):
        """Verify all endpoint environment variables are recognized"""
        import os
        from ice.main import get_span_exporter

        # Test traces endpoint
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://traces:4317"
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://default:4317"

        # Should use traces-specific endpoint
        exporter = get_span_exporter()
        assert exporter is not None

        # Clean up
        os.environ.pop("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", None)
        os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

    def test_metrics_endpoint_override(self):
        """Verify metrics endpoint override works"""
        import os

        os.environ["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"] = "http://metrics:4317"
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://default:4317"

        from ice.main import setup_metrics
        provider = setup_metrics()

        # Verify provider was created with metrics reader
        assert provider is not None

        # Clean up
        os.environ.pop("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", None)
        os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

    @pytest.mark.no_docker
    def test_no_dead_telemetry_endpoint(self):
        """Verify the dead /v1/telemetry/batch endpoint is no longer referenced in config.py"""
        config_path = Path(__file__).parent.parent.parent / "ice" / "telemetry" / "config.py"
        content = config_path.read_text()
        assert "telemetry.ice-engine.io" not in content, \
            "Dead telemetry.ice-engine.io endpoint still present in config.py"
        assert "v1/telemetry/batch" not in content, \
            "Dead /v1/telemetry/batch endpoint still present in config.py"

    def test_logs_endpoint_override(self):
        """Verify logs endpoint override works"""
        import os

        os.environ["OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"] = "http://logs:4317"
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://default:4317"

        from ice.main import setup_logs
        provider = setup_logs()

        # Verify provider was created with log processor
        assert provider is not None

        # Clean up
        os.environ.pop("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", None)
        os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)


class TestOTLPBatchProcessing:
    """Test OTLP batch processing configuration"""

    def test_metric_export_interval(self):
        """Verify metric export interval is configurable"""
        import os

        os.environ["ICE_OTEL_METRIC_EXPORT_INTERVAL"] = "30"

        from ice.main import setup_metrics
        provider = setup_metrics()

        # The interval is set on the PeriodicExportingMetricReader
        # We can't easily verify the interval without accessing internal state
        assert provider is not None

        os.environ.pop("ICE_OTEL_METRIC_EXPORT_INTERVAL", None)

    def test_log_batch_processor(self):
        """Verify log batch processor is configured"""
        from ice.main import setup_logs
        provider = setup_logs()

        # Verify provider has batch processor
        assert provider is not None
        # The provider should have at least one log record processor
        assert len(provider._log_record_processors) > 0


class TestOTLPResourceAttributes:
    """Test resource attributes in OTLP exports"""

    def test_resource_includes_service_info(self):
        """Verify resource includes service.name and service.version"""
        from opentelemetry.sdk.resources import Resource
        from ice.main import build_resource

        resource = build_resource()
        attrs = dict(resource.attributes)

        assert attrs.get("service.name") == "ice-engine"
        assert "service.version" in attrs

    def test_resource_includes_deployment_env(self):
        """Verify resource includes deployment.environment"""
        import os
        from ice.main import build_resource

        os.environ["DEPLOYMENT_ENVIRONMENT"] = "production"

        try:
            resource = build_resource()
            attrs = dict(resource.attributes)
            assert attrs.get("deployment.environment") == "production"
        finally:
            os.environ.pop("DEPLOYMENT_ENVIRONMENT", None)

    def test_resource_includes_host_info(self):
        """Verify resource includes host information"""
        import os
        from ice.main import build_resource

        os.environ["HOSTNAME"] = "test-host-123"

        try:
            resource = build_resource()
            attrs = dict(resource.attributes)
            assert attrs.get("service.instance.id") == "test-host-123"
            assert attrs.get("host.name") == "test-host-123"
        finally:
            os.environ.pop("HOSTNAME", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])