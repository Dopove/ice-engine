<div align="center">
  <h1>🧊 ICE</h1>
  <h3>The One-Import Memory Mandate</h3>
  <p>Throw away the 3,000 lines of brittle memory plumbing you're maintaining. One import. Done.</p>
</div>

---

Your team has already built it: `pgvector` + `Redis` + `custom chunkers` + `prompt assembly` + `session management` + `tenant scoping` + `retrieval heuristics`. It took 6-12 weeks, it's expensive to maintain, and it breaks at 200K tokens.

**ICE is a direct replacement for that entire custom stack.**

We provide a single import that removes the entire engineering problem, and unlike custom implementations, it doesn't have a token limit.

```python
# Your New Stack:
from ice.sdk import init, get_client
```

This documentation provides the **Staff-Engineer level specifications** for integrating and operating the Infinite Context Engine. It is not just another wrapper library; it is a stateless Virtual Memory Manager (VMM) that sits between your applications and any Large Language Model (LLM), providing a 100-Billion Token Horizon with `<100ms` recall latency.

---
## Quickstart
Start the ICE Engine and its backing Semantic Ledger using Docker:

```bash
# 1. Download the ICE Enterprise package and navigate to the docker deployment
cd client_demos/deployment/docker

# 2. Start the Engine, PostgreSQL (pgvector), and Redis
docker compose up -d
```

### Try it out

ICE acts as a transparent proxy. You can use standard `curl` to talk to it exactly like the OpenAI API, but with infinite memory.

Just pass a unique `X-Session-Id` header:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: my-first-project" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "My secret launch code is DELTA-9. Remember this."
      }
    ]
  }'
```

Ask it a question hours, days, or months later using the same session ID. ICE will mathematically page the memory back into the LLM's context window in `<100ms`:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: my-first-project" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "What was my secret launch code?"
      }
    ]
  }'
```

---

## 📚 Official Libraries

ICE provides native, high-performance SDKs for Python and Node.js.

*   [**Python Native SDK**](docs/integration/INTEGRATION.md#1-python-native-sdk-recommended-for-backendai-agents) (PyPI coming soon, currently distributed as `.whl`)
*   [**Node.js Thin Client**](docs/integration/INTEGRATION.md#2-nodejs-thin-client-recommended-for-webapi-servers) (npm coming soon, currently distributed as `.tgz`)

Because ICE is an API proxy, you can also use your favorite existing SDKs just by changing the `base_url`:
*   [OpenAI Python/Node.js SDKs](docs/api_reference/REST_API.md)
*   [Anthropic SDKs](docs/api_reference/REST_API.md)
*   [LangChain / LlamaIndex](docs/api_reference/OLLAMA.md)

---

## 📖 Documentation Directory

### Core Features (How-To Guides)
*   [**Infinite Memory**](features/infinite_memory.md): Using session IDs to retrieve memory hours/months later.
*   [**Multimodal Ingestion**](features/multimodal_rag.md): How to upload PDFs, text files, and codebases.
*   [**Multi-Tenant Isolation**](features/multi_tenant_isolation.md): Isolating user data with PostgreSQL RLS.
*   [**Tool Calling & MCP**](features/tool_calling.md): Using tools, JSON pinning, and Model Context Protocol.

### API & Integration
*   [**REST API Reference**](docs/api_reference/REST_API.md): Endpoints, JSON payloads, and Headers.
*   [**SDK Functions Reference**](docs/api_reference/FUNCTIONS.md): Exhaustive list of Python and Node.js SDK methods.
*   [**Integration Guide**](docs/integration/INTEGRATION.md): How to connect your code using Python, Node.js, or raw HTTP.
*   [**Agentic Tool Calling & MCP**](docs/integration/AGENTIC_TOOL_CALLING.md): How ICE handles JSON parsing and Model Context Protocol (MCP) servers.

### Architecture & Operations
*   [**Theoretical Architecture**](docs/integration/THEORETICAL_ARCHITECTURE.md): The "Singleton Pattern" and how Lead Architects should structure their codebase.
*   [**Configuration Reference**](docs/installation/CONFIGURATION.md): Scaling limits, Memory Caps (`ICE_MEMORY_CAP_GB`), and tuning parameters.
*   [**Operations & Maintenance**](docs/operations/OPERATIONS_GUIDE.md): OpenTelemetry, Prometheus metrics, and Jaeger tracing.
*   [**Data Isolation**](docs/architecture/ISOLATION.md): How ICE uses PostgreSQL Row-Level Security for multi-tenant safety.

### Deployment & Security
*   [**Deployment Guide**](docs/installation/DEPLOYMENT.md): Kubernetes Manifests, HPA auto-scaling, and Docker topologies.
*   [**Enterprise FAQ**](docs/FAQ.md): Answers for CTOs and InfoSec teams (Latency, Cost, Privacy).
*   [**Security & Compliance**](../SECURITY.md): SOC2, GDPR purging utilities, and Vulnerability Disclosure.

---

## 🎮 Interactive Demos

Want to see ICE in action right now? We have built a suite of interactive, highly-visual terminal demos. 

Navigate to the `client_demos/` directory and run:

```bash
cd client_demos
make setup
make py-ollama-demo  # Runs the live Precision Paging stress test
```
*(See `client_demos/README.md` for the full list of available demos, including MCP integration and Multi-Agent tool calling).*