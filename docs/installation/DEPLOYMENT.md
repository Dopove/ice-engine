# 🚀 ICE v2.7.756: Production Deployment Guide

This guide establishes the infrastructure standards for deploying the ICE kernel at scale using Docker and Kubernetes.

---

## 1. Containerization (Docker)

ICE is distributed as a protected Python wheel, making it trivial to containerize for any environment.

### 📍 Dockerfile Strategy
Use the [Dockerfile.example](examples/infrastructure/Dockerfile.example) to build your production image.
*   **Base Image**: `python:3.12-slim` for minimal surface area.
*   **Build Logic**: Install system dependencies (`libpq-dev`) and then `pip install` the protected ICE wheel.

### 📍 Local Orchestration (Docker Compose)
For rapid prototyping or single-node deployments, use [docker-compose.example.yml](examples/infrastructure/docker-compose.example.yml).
```bash
docker-compose up -d
```
This will orchestrate:
1.  **ICE Engine**: The stateless ICE Engine layer.
2.  **PostgreSQL**: Configured with `pgvector` for the semantic ledger.
3.  **Redis**: For hot-context caching.

---

## 2. Enterprise Orchestration (Kubernetes)

ICE is natively stateless, allowing for horizontal scaling across massive K8s clusters.

### 📍 Deployment Architecture
Use the [kubernetes.example.yaml](examples/infrastructure/kubernetes.example.yaml) manifest as a baseline.

*   **Horizontal Scaling**: Set `replicas: 3` (or more) behind a `LoadBalancer`.
*   **ConfigMaps**: Centralize your "Memory Physics" (chunk size, memory caps) in a ConfigMap for global consistency.
*   **Secrets**: Inject your `ICE_LICENSE_JWT` and `DATABASE_URL` via Kubernetes Secrets.

### 📍 Resource Limits (VMM Optimization)
ICE acts as a Virtual Memory Manager. Ensure your pods have sufficient RAM to handle the active "Working Set":
- **Recommended RAM**: 8GB - 32GB (depending on `ICE_MEMORY_CAP_GB`).
- **Recommended CPU**: 4 - 16 Cores (for high-speed semantic synthesis).

---

## 3. CI/CD Integration

DevOps teams should integrate ICE into their automated pipelines:
1.  **Secret Injection**: Use AWS Secrets Manager or HashiCorp Vault to inject the license JWT at deploy time.
2.  **Health Probes**: Configure `livenessProbe` and `readinessProbe` to hit `/v1/health`.
3.  **Metrics**: Scrape the `/metrics` endpoint for Prometheus/Grafana monitoring.

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com  
**(c) 2026 DOPOVE PRIVATE LIMITED**
