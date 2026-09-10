# ICE Telemetry Setup Guide

## Overview

This guide covers setting up telemetry for ICE (Indexless Context Engine) in production environments. ICE provides comprehensive telemetry via OpenTelemetry (OTLP) for traces, metrics, and logs.

## Quick Start

### 1. Enable Telemetry (Default: Enabled)

Telemetry is enabled by default. To disable:

```bash
export ICE_TELEMETRY_ENABLED=false
```

### 2. Configure OTLP Exporter

Point ICE to your OpenTelemetry Collector or observability backend:

```bash
# Required: OTLP gRPC endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# Optional: Separate endpoints for traces/metrics/logs
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4317
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector:4317
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://otel-collector:4317

# Optional: Authentication headers (comma-separated key=value)
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer token123,X-Custom-Header=value"
```

> The SDK client (`RemoteTelemetryClient`) now reuses the same `OTEL_EXPORTER_OTLP_ENDPOINT` variable — the legacy `ICE_TELEMETRY_ENDPOINT` / `/v1/telemetry/batch` HTTP route is no longer used by the client.

### 3. Configure Sampler

Control trace sampling behavior:

```bash
# Default: error_only (only export error spans)
export ICE_OTEL_SAMPLER=error_only

# Options:
# - error_only: Only export spans with errors (default, <1% volume)
# - parent_based_always_on: Always sample if parent sampled
# - traceidratio:0.1 : Sample 10% of traces
# - always_off: Disable trace export
export ICE_OTEL_SAMPLER=traceidratio:0.1
```

### 4. Configure Metric Export Interval

```bash
# Default: 60 seconds
export ICE_OTEL_METRIC_EXPORT_INTERVAL=30
```

### 5. Configure Log Level

```bash
export ICE_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### 6. Resource Attributes (Auto-detected + Optional)

ICE automatically enriches resources with:

| Attribute | Source |
|-----------|--------|
| `service.name` | `ice-engine` |
| `service.version` | `ICE_VERSION` env or `3.1.75` |
| `deployment.environment` | `DEPLOYMENT_ENVIRONMENT` env |
| `service.instance.id` | `HOSTNAME` (K8s pod name) |
| `cloud.region` | `CLOUD_REGION` env |
| `cloud.availability_zone` | `CLOUD_AVAILABILITY_ZONE` env |
| `k8s.cluster.name` | `K8S_CLUSTER_NAME` env |
| `k8s.namespace` | `K8S_NAMESPACE` env |
| `k8s.pod.name` | `K8S_POD_NAME` env |
| `host.name` | `HOSTNAME` env |

Add custom attributes:

```bash
export ICE_OTEL_RESOURCE_ATTRIBUTES="team=platform,owner=platform-team,cost-center=engineering"
```

## Client SDK Telemetry (Remote Collection)

For ICE clients (Python/Node.js SDKs) to send telemetry to your collector:

### Python SDK

```python
from ice import ICE
from ice.telemetry import TelemetryConfig

ice = ICE(
    telemetry=TelemetryConfig(
        endpoint="http://otel-collector:4317",  # OTLP gRPC endpoint
        api_key="sk_live_...",                   # Optional: OTLP headers auth
        sampling_rate=1.0,      # 100% of events
        batch_size=50,          # Batch size
        flush_interval=15,      # seconds
    )
)
```

> The SDK emits via the OTel SDK's built-in OTLP exporter — `compression` is handled OTLP-level (gRPC has its own compression), so the `gzip` option is deprecated and ignored.

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | `true` | Enable/disable telemetry |
| `endpoint` | `http://otel-collector:4317` | OTLP gRPC collector endpoint (read from `OTEL_EXPORTER_OTLP_ENDPOINT`) |
| `api_key` | `""` | Authentication key |
| `sampling_rate` | `1.0` | 0.0-1.0 fraction of events |
| `batch_size` | `50` | Events per batch |
| `flush_interval` | `15` | Seconds between flushes |
| `max_queue_size` | `10000` | Max queued events |
| `timeout` | `10` | HTTP timeout (seconds) |
| `compression` | `gzip` | `gzip` or `none` |

### Privacy Controls (Client-side)

```python
config = TelemetryConfig(
    # ... other config ...
    pii_redaction=True,           # Redact PII from payloads
    hash_identifiers=True,        # Hash tenant/session/user IDs
    anonymize_ips=True,           # Anonymize IP addresses
    allowed_attributes=["service.name", "ice.version"],  # Allowlist
    denied_attributes=["user.email", "user.id", "api_key", "prompt", "completion"]  # Blocklist
)
```

### Automatic Privacy Redaction

The client automatically:
- Hashes `tenant_id`, `session_id`, `user_id` with SHA-256 + salt
- Redacts emails, phone numbers, SSNs, credit cards, API keys
- Anonymizes IP addresses (last octet zeroed)
- Removes denied attributes from payloads

## Server-Side Telemetry Endpoints

### GET /v1/telemetry/status

Returns current telemetry configuration:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  https://ice.yourdomain.com/v1/telemetry/status
```

Response:
```json
{
  "traces": {
    "enabled": true,
    "exporter": "otlp",
    "endpoint": "http://tempo:4317",
    "sampler": "error_only"
  },
  "metrics": {
    "enabled": true,
    "exporter": "otlp",
    "endpoint": "http://prometheus:4317",
    "export_interval_seconds": 60
  },
  "logs": {
    "enabled": true,
    "exporter": "otlp",
    "endpoint": "http://loki:4317",
    "level": "INFO"
  },
  "resource": {
    "service.name": "ice-engine",
    "service.version": "3.1.75",
    "deployment.environment": "production",
    "service.instance.id": "ice-gateway-abc123",
    "cloud.region": "us-east-1",
    "k8s.cluster.name": "ice-prod",
    "k8s.namespace": "ice"
  },
  "propagator": "tracecontext"
}
```

### POST /v1/telemetry/force-flush

Force flush all telemetry pipelines:

```bash
curl -X POST -H "Authorization: Bearer $API_KEY" \
  https://ice.yourdomain.com/v1/telemetry/force-flush
```

Response:
```json
{
  "flushed": {
    "traces": true,
    "metrics": true,
    "logs": true
  },
  "status": "completed"
}
```

### Data Export (GDPR Compliance)

```bash
# Export all telemetry for a tenant
curl -H "Authorization: Bearer $API_KEY" \
  "https://ice.yourdomain.com/v1/telemetry/export?tenant_id=tenant-123&start=2024-01-01&end=2024-12-31"
```

### Data Deletion (GDPR Right to be Forgotten)

```bash
curl -X DELETE -H "Authorization: Bearer $API_KEY" \
  "https://ice.yourdomain.com/v1/telemetry/data?tenant_id=tenant-123"
```

## Client SDK Integration

### Python

```python
from ice import ICE
from ice.telemetry import TelemetryConfig

ice = ICE(
    telemetry=TelemetryConfig(
        endpoint="http://otel-collector:4317",  # OTLP gRPC endpoint
        api_key="sk_live_..."
    )
)

# Telemetry automatically emitted on:
# - ice.chat.completions.create()
# - ice.ingest()
# - Any kernel operation
```

### Node.js

```javascript
const { ICE, TelemetryConfig } = require('ice-sdk');

const ice = new ICE({
  telemetry: new TelemetryConfig({
    endpoint: 'http://otel-collector:4317',  // OTLP gRPC
    apiKey: 'sk_live_...',
    samplingRate: 1.0,
    batchSize: 50,
    flushInterval: 15000
  })
});

// Automatic telemetry on chat completions
const response = await ice.chat.completions.create({
  model: 'ministral-3:3b',
  messages: [{ role: 'user', content: 'Hello' }]
});
```

## Telemetry Data Schema

### OTLP Payload

Telemetry is emitted via OTLP (gRPC `4317` / HTTP `4318`). The client SDK queues payloads and converts them onto the OTel SDK's span processor — there is no custom batch HTTP endpoint.

```json
{
  "traces": [
    {
      "trace_id": "abc123...",
      "span_id": "def456...",
      "parent_span_id": "parent789...",
      "name": "generate_ice_chunks",
      "kind": "SERVER",
      "start_time": 1704067200000000000,
      "end_time": 1704067205000000000,
      "attributes": {
        "ice.tenant_id": "a1b2c3d4...",
        "ice.session_id": "sess_abc123",
        "ice.user_id": "user_123",
        "ice.model": "ministral-3:3b",
        "ice.provider": "openai",
        "http.status_code": 200
      },
      "status": { "code": "OK" },
      "events": [
        { "name": "upstream_request", "timestamp": 1704067200100000000, "attributes": {} }
      ]
    }
  ],
  "metrics": [
    {
      "name": "ice_upstream_latency_seconds",
      "type": "histogram",
      "data_points": [
        {
          "timestamp": 1704067205000000000,
          "value": 1.234,
          "attributes": {
            "provider": "openai",
            "model": "gpt-4",
            "tenant_id": "a1b2c3d4..."
          }
        }
      ]
    },
    {
      "name": "ice_upstream_errors_total",
      "type": "counter",
      "data_points": [
        {
          "timestamp": 1704067205000000000,
          "value": 1,
          "attributes": {
            "provider": "anthropic",
            "error_type": "rate_limit",
            "tenant_id": "a1b2c3d4..."
          }
        }
      ]
    }
  ],
  "logs": [
    {
      "timestamp": 1704067205000000000,
      "severity_text": "INFO",
      "severity_number": 9,
      "body": "Stitcher: Completed turn 3/10",
      "attributes": {
        "ice.tenant_id": "a1b2c3d4...",
        "ice.session_id": "sess_abc123",
        "code.function": "generate_ice_chunks",
        "code.filepath": "ice/main.py",
        "code.lineno": 1234
      }
    }
  ]
}
```

## Key Metrics Reference

### Traces (Tempo)

| Span Name | Description |
|-----------|-------------|
| `generate_ice_chunks` | Main generation loop |
| `EpisodicManager.save_message` | Save message to episodic memory |
| `EpisodicManager.search_episodic` | Semantic search |
| `EpisodicManager.search_local_episodic` | Local vector search |
| `ReasoningManager.save_trace` | Save reasoning trace |
| `ReasoningManager.search_reasoning` | Search reasoning traces |
| `get_cached_embedding` | Embedding cache lookup |
| `retention_purge_cycle` | Daily retention cleanup |
| `db_metrics_loop` | DB pool metrics |

### Metrics (Prometheus)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ice_total_queries` | Counter | - | Total queries processed |
| `ice_generation_latency_seconds` | Histogram | - | End-to-end generation latency |
| `ice_upstream_latency_seconds` | Histogram | `provider`, `model` | Upstream LLM latency |
| `ice_upstream_errors_total` | Counter | `provider`, `error_type` | Upstream errors by type |
| `ice_tokens_input_total` | Counter | `tenant_id`, `provider` | Input tokens sent |
| `ice_tokens_output_total` | Counter | `tenant_id`, `provider` | Output tokens received |
| `ice_active_sessions` | Gauge | `tenant_id` | Active sessions |
| `ice_degraded_mode` | Gauge | - | 1 if degraded, 0 if healthy |
| `ice_circuit_breaker_state` | Gauge | `provider` | 0=closed, 1=open, 2=half-open |
| `ice_chunk_generation_duration_seconds` | Histogram | - | Per-turn generation time |
| `ice_retrieval_latency_seconds` | Histogram | `search_type` | Search latency (local/remote/demo) |
| `ice_tokens_input_total` | Counter | `tenant_id`, `provider` | Input tokens |
| `ice_tokens_output_total` | Counter | `tenant_id`, `provider` | Output tokens |
| `ice_chunk_generation_duration_seconds` | Histogram | - | Per-turn latency |
| `ice_active_sessions` | Gauge | `tenant_id` | Active sessions |
| `ice_license_tier` | Gauge | `sku` | 1=community, 2=dev-pro, 3=enterprise |
| `ice_degraded_mode` | Gauge | - | Degraded mode indicator |
| `ice_stitch_semaphore_locked` | Gauge | - | Active stitch operations |
| `ice_retrieval_latency_seconds` | Histogram | `search_type` | Search latency |

### Logs (Loki)

| Field | Description |
|-------|-------------|
| `timestamp` | Unix nanoseconds |
| `level` | DEBUG/INFO/WARNING/ERROR |
| `message` | Log message |
| `trace_id` | W3C trace ID (32 hex chars) |
| `span_id` | W3C span ID (16 hex chars) |
| `module` | Python module |
| `function` | Function name |
| `line` | Line number |
| `ice.tenant_id` | Hashed tenant ID |
| `ice.session_id` | Hashed session ID |

## Grafana Dashboards

Import these dashboards from `deploy/grafana/dashboards/`:

1. **ICE Client Health** - Per-tenant sessions, degraded mode, errors
2. **ICE Usage** - Queries, tokens, latency by client/version
3. **Gateway Health** - Latency, error rate, queue depth
4. **Ingestion Pipeline** - Throughput, queue lag, retry rate

## Alerting Rules

Key alerts (defined in `deploy/terraform/modules/monitoring/main.tf`):

| Alert | Condition | Severity |
|-------|-----------|----------|
| `client_degraded` | `ice_degraded_mode == 1` for 5m | Critical |
| `client_high_errors` | `rate(ice_upstream_errors_total[5m]) > 0.1` | Warning |
| `gateway_unhealthy` | `gateway_up == 0` for 1m | Critical |
| `ingestion_lag` | `ingestion_queue_size > 10000` | Warning |

## Troubleshooting

### No Traces Appearing

1. Check `ICE_TELEMETRY_ENABLED=true`
2. Verify `OTEL_EXPORTER_OTLP_ENDPOINT` is reachable
3. Check `ICE_OTEL_SAMPLER` - `error_only` only exports errors
4. Check firewall/security groups for port 4317

### No Metrics in Prometheus

1. Check `ICE_OTEL_METRIC_EXPORT_INTERVAL`
2. Verify `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`
3. Check Prometheus service monitor for `ice-engine`

### High Latency

1. Check `ice_upstream_latency_seconds` by provider
2. Check circuit breaker state: `ice_circuit_breaker_state`
3. Review `ice_generation_latency_seconds` for end-to-end

### No Logs in Loki

1. Check `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`
2. Verify log level: `ICE_LOG_LEVEL`
3. Check Loki ingester logs

---

## Support

- **Documentation:** https://docs.ice-engine.io/telemetry
- **Issues:** https://github.com/ice-engine/ice/issues
- **Security:** security@ice-engine.io