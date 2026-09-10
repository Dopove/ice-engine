---
type: operations
title: Deployment & Observability Infrastructure
description: The Terraform-managed AWS deployment — ECS gateway plus ADOT collector/Loki sidecars, networking, CloudWatch monitoring, S3/Athena telemetry archival, and the Docker image — including several alarm and Athena-schema defects.
tags: [terraform, aws, ecs, fargate, cloudwatch, s3, athena, docker, deployment]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-a60ace5ac7d2819c862c72bf
    resource: repo://deploy/terraform/modules/ecs-gateway/main.tf
  - id: openwiki-source-9efdd3ab9916bfee84bf8481
    resource: repo://deploy/terraform/modules/monitoring/main.tf
  - id: openwiki-source-3b02b9daad2882f8fe4618cc
    resource: repo://deploy/terraform/modules/networking/main.tf
  - id: openwiki-source-9621a9999face5522948f21d
    resource: repo://deploy/terraform/modules/s3-telemetry/main.tf
  - id: openwiki-source-bb1ebe868e35e9e500714501
    resource: repo://Dockerfile
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Shape of the deployment

`deploy/terraform/main.tf` wires together six modules under one VPC: `networking` (VPC/subnets/ALB), `secrets`, `s3_telemetry`, `ecs_gateway` (the gateway plus its ADOT collector and Loki sidecars), `eks_observability` (an EKS cluster whose node group is tainted `workload-type=observability`, provisioned for Tempo/Loki/Grafana/Prometheus IRSA roles and S3 buckets), `monitoring` (CloudWatch alarms/dashboard/SNS), and `grafana` (a separate module wiring an AWS Managed Grafana-style workspace). The gateway and its telemetry sidecars run on ECS Fargate; the EKS cluster exists primarily to host the observability stack's IRSA identities and S3-backed storage, not the gateway itself.

## Networking (`modules/networking`)

Standard 3-tier VPC: public subnets with an Internet Gateway, private subnets each with their own NAT Gateway (one per AZ for HA), and three security groups (`alb`, `ecs`, `eks`) with a layered ingress model — ALB accepts 80/443 from anywhere, ECS accepts 8080 from the ALB SG and 4317 (OTLP gRPC) from itself, EKS accepts 443/4317 from the ECS SG and 3000 (Grafana) from the ALB SG. The ALB is internet-facing with access logging to a dedicated, encrypted, public-access-blocked S3 bucket. TLS (`aws_acm_certificate` + DNS validation via Route53) and the HTTPS listener/HTTP→HTTPS redirect are conditional on `var.domain_name` being set — with no domain, only the resources gated by `count = var.domain_name != "" ? 1 : 0` are skipped, so the module can stand up without a custom domain.

## ECS gateway + telemetry sidecars (`modules/ecs-gateway`)

- **`ice_gateway`** — the Fargate task/service for `ice.main:app`, health-checked via `/live`, registered with the ALB target group. Its container environment sets both the OTLP env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`/`_HEADERS`) and the legacy `ICE_TELEMETRY_ENDPOINT`/`ICE_TELEMETRY_API_KEY` vars — see [[telemetry]] for which of these the application code actually uses.
- **`otel_collector`** and **`loki`** — sibling Fargate services on the same cluster, each registered in a private DNS namespace (`ice.internal`, via AWS Cloud Map / `aws_service_discovery_*`) so the gateway and collector can resolve each other by name (`collector.ice.internal:4317`, `loki.ice.internal:3100`) without hardcoded IPs. The collector's config is rendered from a `.tftpl` template and passed in via an `OTEL_CONFIG_CONTENT` environment variable rather than a mounted file.
- All three services share the same `ecs_execution_role` and `ecs_task_role` — there's no per-service IAM scoping between the gateway, collector, and Loki tasks.
- The task role's `telemetry_policy` grants S3 access to both the `<env>-ice-telemetry-*` buckets and the Loki bucket, plus X-Ray trace-segment write permissions — consistent with traces going to X-Ray and logs going to the self-hosted Loki, rather than to the S3/Athena telemetry pipeline described below.
- **Defect:** `aws_ecs_service.ice_gateway` declares the `deployment_circuit_breaker` nested block **twice** with identical content. This block is not a repeatable list in the AWS provider's schema (max one instance) — `terraform validate`/`plan` would reject this configuration ("no more than 1 \"deployment_circuit_breaker\" blocks are allowed") as written.

## Monitoring (`modules/monitoring`)

CloudWatch alarms cover ALB latency/errors/health, ECS CPU/memory/task-count, RDS CPU/connections, ElastiCache memory, and a custom `Custom/ICE` telemetry-queue-lag alarm — all routed to one SNS topic (`aws_sns_topic.alerts`), with an optional email subscription. A `aws_cloudwatch_dashboard` aggregates the same metric families into four widgets.

- **Defect — nonexistent metric:** `gateway_high_latency` sets `namespace = "AWS/ApplicationELB"` with `metric_name = "Latency"`. The ALB namespace does not publish a metric literally named `Latency` (that name belongs to the legacy Classic ELB namespace, `AWS/ELB`); the ALB equivalent is `TargetResponseTime`, which the *other*, seemingly-redundant alarm two blocks below (`gateway_high_latency_p99`, threshold 5000ms) correctly uses. Because `treat_missing_data = "notBreaching"`, `gateway_high_latency` will simply never have data and will never fire, silently.
- **Defect — invalid statistic:** Both `gateway_high_latency` and `gateway_high_latency_p99` set `statistic = "p99"`. The `aws_cloudwatch_metric_alarm` resource's `statistic` argument only accepts the standard CloudWatch statistics (`SampleCount`, `Average`, `Sum`, `Minimum`, `Maximum`); a percentile like `p99` must instead be supplied via the separate `extended_statistic` argument. As written, both alarms would fail `terraform apply` (or the underlying `PutMetricAlarm` API call) with an invalid-statistic error — this is a second, independent reason `gateway_high_latency_p99` cannot work as configured, on top of `gateway_high_latency`'s wrong metric name.
- The dashboard's own widget JSON is unaffected by this — CloudWatch dashboard widget metric arrays accept a `stat: "p99"` option directly in their properties object, which is a different (and valid) mechanism from the `aws_cloudwatch_metric_alarm` resource's `statistic`/`extended_statistic` arguments.

## S3 telemetry archival (`modules/s3-telemetry`)

Two encrypted, public-access-blocked S3 buckets (`<name>-raw`, 365-day expiry; `<name>-aggregated`, 7-year/2555-day expiry) plus an Athena workgroup/database and three named queries that `CREATE EXTERNAL TABLE` definitions for `traces`, `metrics`, and `logs`, each partitioned by `year`/`month`/`day` with partition projection and pointed at `s3://<raw-bucket>/{traces,metrics,logs}/...` as Parquet.

- **Defect — duplicate argument:** `aws_athena_named_query.traces_table` assigns the `workgroup` argument twice within the same resource block (once near the top, once at the bottom, both to the same value). Terraform's HCL parser rejects a block with the same argument name assigned more than once — this resource fails to parse/validate as written.
- **Gap — nothing populates these buckets:** No code anywhere in `ice/` writes objects to S3 (there is no `s3_client`/`put_object`/`boto3.client("s3")` usage in the application; the only `boto3` usage is the Secrets Manager lookup in `ice/main.py` — see [[gateway-api]]). This Athena/S3 pipeline's raw and aggregated buckets, and the three table definitions expecting partitioned Parquet at fixed prefixes, have no corresponding ETL or ingestion path in this tree — the actual telemetry pipeline routes traces/metrics/logs to X-Ray/Prometheus/Loki via the ADOT collector (see [[telemetry]]), not to S3.

## Docker image

The `Dockerfile` is a two-stage build: a `builder` stage installs build tooling (gcc/g++/cmake/pkg-config/libpq-dev) and both `requirements.txt` and `test_requirements.txt` into the image; the `runtime` stage copies only the installed site-packages and application code onto a slim Python 3.12 base, running as a non-root `ice` user (uid/gid 1000) with a `HEALTHCHECK` against `/live` and `CMD ["python", "-m", "ice.main"]`. Notably, `test_requirements.txt` is installed into the final image via the builder-stage site-packages copy — test dependencies ship in the production image, not just the build stage.
