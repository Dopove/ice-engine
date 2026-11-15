# SPDX-License-Identifier: MIT

"""
ICE Remote Telemetry Emitter

Telemetry emission routed through the OpenTelemetry SDK to OTLP.
"""

import asyncio
import time
import random
import logging
from typing import Dict, Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from .config import TelemetryConfig
from .privacy import redact_pii

logger = logging.getLogger("ice_telemetry")


class RemoteTelemetryClient:
    """
    Client for emitting telemetry via the OpenTelemetry SDK to an OTLP collector.

    Features:
    - Routes client-side telemetry through OTLP (no custom HTTP endpoint)
    - Queue-based buffering for backpressure handling
    - Graceful shutdown with flush
    """

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self._tracer_provider: Optional[TracerProvider] = None
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Configure the OTLP exporter and start the background flush task."""
        if self._running:
            return

        # Build resource attributes (service name + version, sampled)
        resource = Resource.create(
            attributes={
                "service.name": "ice-sdk",
                "telemetry.sdk.language": "python",
            }
        )

        # Traces → OTLP gRPC
        self._tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(
            endpoint=self.config.endpoint,
            insecure=True,
        )
        self._tracer_provider.add_span_processor(
            BatchSpanProcessor(span_exporter, max_batch_size=self.config.batch_size)
        )
        trace.set_tracer_provider(self._tracer_provider)

        # Metrics → OTLP gRPC (periodically exported)
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=self.config.endpoint, insecure=True),
            export_interval_millis=self.config.flush_interval * 1000,
        )
        meter_provider = SdkMeterProvider(resource=resource, metric_readers=[metric_reader])
        get_meter_provider()  # ensures no-op default
        set_meter_provider(meter_provider)

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Telemetry emitter started (OTLP endpoint: %s)", self.config.endpoint)

    async def stop(self):
        """Stop the emitter and flush remaining spans/metrics."""
        if not self._running:
            return

        self._running = False

        # Wait for flush task to complete current batch
        if self._flush_task:
            try:
                await asyncio.wait_for(self._flush_task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Telemetry flush task timed out during shutdown")

        # Flush any remaining items
        await self._flush_batch()

        # Flush OTel providers
        if self._tracer_provider:
            self._tracer_provider.force_flush()
            self._tracer_provider.shutdown()

        logger.info("Telemetry emitter stopped")

    async def emit(self, payload: Dict[str, Any]) -> bool:
        """
        Queue a telemetry payload for emission.

        Returns:
            True if queued, False if dropped (queue full or disabled)
        """
        if not self.config.enabled:
            return False

        # Sampling
        if random.random() > self.config.sampling_rate:
            return False

        # Apply privacy redaction
        from .privacy import redact_pii
        payload = redact_pii(payload, self.config)

        try:
            self._queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            logger.warning("Telemetry queue full, dropping payload")
            return False

    async def emit_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Emit a metric payload."""
        await self.emit({
            "type": "metric",
            "timestamp": time.time(),
            "name": name,
            "value": value,
            "labels": labels or {}
        })

    async def emit_trace(self, trace_data: Dict[str, Any]):
        """Emit a trace payload."""
        await self.emit({
            "type": "trace",
            "timestamp": time.time(),
            "data": trace_data
        })

    async def emit_log(self, level: str, message: str, attributes: Dict[str, Any] = None):
        """Emit a log payload."""
        await self.emit({
            "type": "log",
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "attributes": attributes or {}
        })

    async def _flush_loop(self):
        """Background task that periodically flushes the queue."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                if self._running:  # Double-check after sleep
                    await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telemetry flush loop error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry

    async def _flush_batch(self):
        """Flush a batch of queued payloads."""
        if self._queue.empty():
            return

        batch = []
        while not self._queue.empty() and len(batch) < self.config.batch_size:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        await self._send_batch(batch)

    async def _send_batch(self, batch: list):
        """Convert queued payloads onto the OTLP SDK span processor.

        The BatchSpanProcessor (added to the TracerProvider in start()) handles
        batching, retries, and backoff to the OTLP collector — so we just feed
        each queued record onto a span.  Metrics logs through the PeriodicExporting
        MetricReader.  This replaces the former JSON-over-HTTP batch send to the now-
        removed /v1/telemetry/batch endpoint.
        """
        if not self._tracer_provider:
            logger.warning("No tracer provider available for telemetry")
            return

        tracer = trace.get_tracer("ice-telemetry", "1.0")
        failed = []

        for item in batch:
            try:
                item_type = item.get("type", "generic")
                if item_type == "trace":
                    with tracer.start_as_current_span("ice.sdk.operation") as span:
                        span.set_attribute("telemetry.type", "trace")
                        _attrs = redact_pii(item.get("data", {}), self.config)
                        for k, v in _attrs.items():
                            span.set_attribute(k, str(v))
                elif item_type == "metric":
                    meter = get_meter_provider().get_meter("ice.sdk.metrics")
                    counter = meter.create_counter(item.get("name", "ice.metric"))
                    counter.add(item.get("value", 0), item.get("labels", {}))
                elif item_type == "log":
                    with tracer.start_as_current_span("ice.sdk.log") as span:
                        span.set_attribute("telemetry.type", "log")
                        span.set_attribute("log.level", item.get("level", ""))
                        span.set_attribute("log.message", item.get("message", ""))
                else:
                    with tracer.start_as_current_span("ice.sdk.event") as span:
                        span.set_attribute("telemetry.type", "generic")
                        attrs = redact_pii(item, self.config)
                        for k, v in attrs.items():
                            span.set_attribute(k, str(v))
            except Exception as e:
                logger.warning(f"Failed to emit telemetry item: {e}")
                failed.append(item)

        # Flush the SDK spans so they hit the collector immediately
        self._tracer_provider.force_flush()

        if failed:
            logger.warning(f"{len(failed)} telemetry items could not be emitted this batch")