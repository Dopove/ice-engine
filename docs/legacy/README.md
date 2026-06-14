<div align="center">
  <h1>🧊 ICE</h1>
  <h3>Context Management, Not Just Context Size</h3>
  <p>The network-layer Virtual Memory Management Unit (VMM) for LLMs.</p>
</div>

---

Everyone is chasing "infinite context windows," but stuffing 1 million tokens into an LLM destroys your Time-To-First-Token (TTFT), blows up your API bill, and models still suffer from "Lost in the Middle" attention failure.

**ICE is not an infinite prompt string. It is a network-layer Virtual Memory Management Unit (VMM).** We use a strict "Truncation Guillotine" to keep the physical prompt size mathematically dense and cheap.

By maintaining an external 100-Billion Token Semantic Ledger in Postgres, ICE acts as an operating system for your LLM. It intercepts the request, pages the exact relevant facts and tool results into the highest-attention zones of the prompt, and truncates the noise before the GPU ever sees it.

---

## 🗡️ The Three "Killers" You Get Out-of-the-Box

We aren't just selling "more tokens." We are selling the eradication of three specific, expensive production failures:

### 1. The Cure for "Agentic Amnesia"
**The Problem:** Autonomous agents build massive JSON histories of `tool_calls` and `tool_results`. Within 10 steps, this history blows out the context window, and the agent forgets the result of Step 1.
**The ICE Solution:** ICE intercepts native tool syntax (OpenAI/Anthropic/Gemini). It pins the most recent, critical tool results directly to the prompt and archives older results to the Semantic Ledger. If the agent needs Step 1 during Step 20, ICE pages it back in automatically.

### 2. The Cure for the "Attention Problem" (Multi-Tiered Injection)
**The Problem:** Compacting or summarizing old messages destroys high-resolution details (like exact code snippets or JSON structures).
**The ICE Solution:** ICE does not summarize. It uses **Precision Paging** to inject raw, unadulterated facts from the ledger. It physically pins the System Prompt and Reasoning Traces to the "Floor" (highest attention), places the recent query at the "Ceiling," and injects the retrieved facts into the dense middle.

### 3. The Cure for Cross-Tenant Data Leakage
**The Problem:** Building RAG for multi-tenant SaaS requires brittle, custom application-layer routing to ensure User A never sees User B's embeddings.
**The ICE Solution:** ICE enforces multi-tenancy at the database kernel. It uses PostgreSQL Row-Level Security (`SET LOCAL ice.current_tenant_id`). It is physically impossible for an LLM to hallucinate or retrieve another user's data.

---

## 🚀 The Closing Roadmap Promise

Right now, if you paste a 500K-token monolithic file into the chat array, ICE will truncate it to enforce token efficiency. For large files, you must use our `/v1/ingest` pipeline first. 

**However, because our architecture is built entirely in C and Python, we are actively migrating the ingestion engine to the Resonant C Compiler (RCC).** 
Soon, you will be able to paste a 1-million token codebase directly into the prompt, and our RCC backend will vectorize and index it in milliseconds via Tensor Cores before the LLM even responds.

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

*   [**Python Native SDK**](docs/integration/INTEGRATION.md#1-python-native-sdk-recommended-for-backendai-agents) (PyPI coming soon)
    *   **Supported Versions:** Python 3.10, 3.11, 3.12
    *   **Architectures:** `x86_64` and `aarch64`
    *   Separate wheels are provided for each SKU and platform combination.
*   [**Node.js Thin Client**](docs/integration/INTEGRATION.md#2-nodejs-thin-client-recommended-for-webapi-servers) (npm coming soon)
    *   **Packages:**
        *   `ice-node-community`: For Community and Developer Pro tiers.
        *   `ice-node-enterprise`: For the Enterprise tier.
        *   `ice-node-unlimited`: For the Unlimited tier.

Because ICE is an API proxy, you can also use your favorite existing SDKs just by changing the `base_url`:
*   [OpenAI Python/Node.js SDKs](docs/api_reference/REST_API.md)
*   [Anthropic SDKs](docs/api_reference/REST_API.md)
*   [LangChain / LlamaIndex](docs/api_reference/OLLAMA.md)

---

## 📖 Documentation Directory

### Core Features (How-To Guides)
*   [**Infinite Memory**](features/infinite_memory.md): Using session IDs to retrieve memory hours/months later.
*   [**Workspace Mount**](features/workspace_mount.md): The enterprise solution for massive input context.
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
*   [**Federated Search**](docs/architecture/FEDERATED_SEARCH.md): Deploy ICE across multiple instances for global scale.
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