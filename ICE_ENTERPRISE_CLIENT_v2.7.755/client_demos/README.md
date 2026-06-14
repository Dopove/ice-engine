# 🎓 ICE Developer Experience (DX) & Onboarding Hub

Welcome to the **Interactive Demos Suite** for the Infinite Context Engine (ICE) v2.7.756.

This directory is designed to give you a "perfect DX" right out of the box. Instead of reading endless documentation and guessing how to write the code, we provide exact, runnable, copy-pasteable examples for every single enterprise feature in both **Python** and **Node.js**.

## 🚀 Quick Setup (1-Click Install)

We have bundled a unified `Makefile` to instantly install all SDK variants and their dependencies (`fastapi`, `express`, `asyncpg`, etc.).

```bash
cd client_demos/
make setup
```
*This command will install the local IP-protected `.whl` and `.tgz` Native SDKs provided in your enterprise distribution.*

---

## 🎮 The Command Center

You can execute any demo effortlessly using the `make` command from this directory. Run `make help` to see the full interactive menu:

```bash
make help
```

### 1. Core Feature Demonstrations
Understand the memory physics of ICE in isolated scripts.
*   `make py-chat` / `make node-chat`: Basic infinite context retrieval.
*   `make py-ollama-demo`: Live Ollama Precision Paging stress test.
*   `make py-agent` / `make node-agent`: Tool calling and syntax defense.
*   `make py-rot` / `make node-rot`: The mathematical prevention of "Context Rot".
*   `make py-isolation` / `make node-isolation`: Absolute Session & Tenant Isolation.
*   `make py-adv-agent` / `make node-adv-agent`: Advanced Multi-Step Tool Calling.
*   `make py-mcp` / `make node-mcp`: Model Context Protocol (MCP) Integration.

*   **API Server Architectures** (The "Singleton Kernel" Pattern)
    See exactly how a Lead Architect structures a production FastAPI or Express API server using the "Singleton Kernel Pattern".
    *   `make py-api` (Starts a simpler FastAPI server on port 8080)
    *   `make py-enterprise-api` (Starts the **Comprehensive Enterprise API Example** with all customizations and detailed comments on port 8000)
    *   `make node-api` (Starts an Express server on port 3000)

### 3. CLI Terminal Agents (Claude Code / Gemini-CLI style)
Learn how to build lightweight terminal tools that permanently bind their memory to the local workspace folder.
*   `make py-cli` / `make node-cli`

### 4. Connectivity & Session Management
Learn the 3 primary integration methods to securely pass `x-session-id` and `x-user-id` to the Engine.
*   `make py-session-http` (Stateless REST Headers)
*   `make py-session-jwt` (Secure Web App Cookies & JWTs)
*   `make py-session-ws` (Ultra-low latency WebSocket streaming)

---

\n## 🔬 Engineering Proofs
For technical deep-dives, we provide standalone proof scripts that mathematically verify the core physics of the ICE Kernel.
*   `make py-proof-attention`: Empirically proves that the `ContextPager` mitigates the "Lost in the Middle" problem via Multi-Tiered Injection.

## 🛠️ DevOps & Enterprise Governance

Beyond code, we provide the actual infrastructure manifests and compliance scripts your DevOps team needs.

*   **`deployment/`**: Production-ready `docker-compose.yml` and Kubernetes (`k8s/`) manifests demonstrating stateless HPA scaling and config maps.
*   **`observability/`**: An OpenTelemetry stack with Jaeger, Prometheus, and Grafana to visualize token metrics and RAG latency.
*   **`testing/`**: A guide (`pytest_mocking_guide.py`) on utilizing the offline `mock_client()` for zero-cost CI/CD pipeline validation.
*   **`data_governance/`**: Python utility (`gdpr_deletion_script.py`) to execute hard cryptographic purges of specific tenants/users for GDPR "Right to be Forgotten" requests.

Enjoy the frictionless power of the Infinite Context Engine.
