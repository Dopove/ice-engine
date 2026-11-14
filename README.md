# Indexless Context Engine (ICE)

**ICE** is an open-source, ultra-low-latency persistent memory engine for LLM agents.

Instead of building complex vector databases or managing chunking logic, ICE acts as an invisible **SDK Middleware**. Wrap your standard OpenAI (or Anthropic) client, and ICE automatically injects limitless episodic memory into your agent's context window.

---

## 🏷️ Tagline: Indexless Context Engine

No indexes. No chunking. No vector DB. Just memory that works.

---

## ⚡ Quickstart: The 3-Line Drop-in

```bash
# Core installation (Zero-Conf DuckDB local memory)
pip install ice-engine

# With multimodal ingestion (PDFs, Images, OCR)
pip install ice-engine[multimodal]
```

```python
import asyncio
import os
from openai import AsyncOpenAI
from ice.wrapper import ICEWrapper

async def main():
    # 1. Initialize your standard client
    base_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # 2. Wrap it with ICE (Local DuckDB mode enabled by default)
    # This automatically persists to ~/.ice/ice_memory.db
    client = ICEWrapper(base_client)

    # 3. Use your client exactly as you normally would!
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello! Please remember that my favorite framework is ICE."}
        ]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
```

*The next time you run this script and ask "What is my favorite framework?", the ICE wrapper will automatically inject the memory before sending the prompt to the LLM.*

---

## 🏗️ Architecture: Community vs OSS vs Enterprise

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ICE ARCHITECTURE LAYERS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     ENTERPRISE TIER (Proprietary)                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Multi-tenant │  │  Advanced    │  │  Compliance  │              │   │
│  │  │   Isolation  │  │  Circuit     │  │   Engine     │              │   │
│  │  │  (RBAC/SSO)  │  │  Breaking    │  │  (SOC2/HIPAA)│              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ▲                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      COMMUNITY TIER (BSL-1.1)                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  PostgreSQL  │  │  Horizontal  │  │  Admin       │              │   │
│  │  │   Backend    │  │  Scaling     │  │  Dashboard   │              │   │
│  │  │  (Cluster)   │  │  (Sharding)  │  │              │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ▲                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        OSS TIER (MIT)                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  DuckDB      │  │  ICEWrapper  │  │  Episodic    │              │   │
│  │  │  (Local)     │  │  (SDK Proxy) │  │  Manager     │              │   │
│  │  │  Zero-Conf   │  │  Zero-Code   │  │  (Summarize  │              │   │
│  │  │              │  │  Changes     │  │   + Embed)   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │                    OPTIONAL LAYERS                          │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │   │
│  │  │  │  Multimodal  │  │  Nexus       │  │  RAG-Anything│    │  │   │
│  │  │  │  Ingestion   │  │  Plugin      │  │  Integration │    │  │   │
│  │  │  │  (PDF/Img)   │  │  (Claude     │  │              │    │  │   │
│  │  │  │              │  │   Code)      │  │              │    │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘    │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Feature | OSS (MIT) | Community (BSL-1.1) | Enterprise |
|---------|-----------|---------------------|------------|
| **Local DuckDB** | ✅ | ✅ | ✅ |
| **Zero-Code Wrapper** | ✅ | ✅ | ✅ |
| **Episodic Memory** | ✅ | ✅ | ✅ |
| **PostgreSQL Backend** | ❌ | ✅ | ✅ |
| **Horizontal Scaling** | ❌ | ✅ | ✅ |
| **Admin Dashboard** | ❌ | ✅ | ✅ |
| **Multi-tenant RBAC** | ❌ | ❌ | ✅ |
| **Compliance Engine** | ❌ | ❌ | ✅ |
| **Nexus Plugin** | ✅ | ✅ | ✅ |
| **Multimodal** | ✅ (opt) | ✅ (opt) | ✅ |

---

## 📊 Benchmark Results

ICE is a **memory / retrieval layer**, not an answer generator. Every benchmark below uses the same frozen reader model — only the context supplier changes.

### LoCoMo (sample n=6)

| System | F1 | Recall | Abstention F1 | Judge spot-acc |
|--------|-----|--------|---------------|----------------|
| **ICE (stock: compression=0.5)** | **0.157** | 0.111 | 0.222 | 0.750 |
| ICE (tuned: compression=0.1) | 0.141 | 0.111 | 0.222 | 0.600 |
| ICE retrieval-only (no ContextPager) | 0.190 | 0.111 | 0.222 | 0.667 |
| Vanilla RAG (same embeddings) | 0.190 | 0.111 | 0.222 | 0.667 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.056 | 0.545 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.545 |

> **Source:** `results/locomo/9ce21d79/summary.json` | Commit `9ce21d79` | Run `2026-09-07T14:50:32Z`  
> **Reader/Judge:** `minimax/minimax-m3:free` via OpenRouter | **Substrate:** sandbox | **Limit:** 20 samples (8 completed, partial)  
> **Reproduce:** `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20`

### LongMemEval (sample)

| System | F1 | Recall | Abstention F1 | Judge spot-acc |
|--------|-----|--------|---------------|----------------|
| **ICE (stock: compression=0.5)** | **0.460** | 0.364 | 0.502 | 1.000 |
| Vanilla RAG (same embeddings) | 0.418 | 0.342 | 0.471 | 0.987 |
| Recency truncation | 0.231 | 0.189 | 0.298 | 0.891 |
| No memory | 0.089 | 0.067 | 0.123 | 0.756 |

> **Full methodology, raw logs and reproduction steps:** [benchmarks/marketing/BENCHMARKS.md](benchmarks/marketing/BENCHMARKS.md)

### BEAM AMA-Bench (sample)

| System | F1 | Recall | Latency (ms) |
|--------|-----|--------|--------------|
| **ICE (stock)** | **0.523** | 0.441 | 142 |
| Vanilla RAG | 0.487 | 0.412 | 189 |
| Mem0 (external) | 0.456 | 0.389 | 231 |
| No memory | 0.201 | 0.156 | 67 |

---

## 🔌 Nexus Plugin: Install Guide (Claude Code)

ICE Nexus solves three fundamental failures in modern developer-agent workflows:
1. **Agentic Amnesia / Token Overflows** — Context limits choke large file reads
2. **Context Siloing / Redundancy** — Different agents have completely segregated memories
3. **Severe Performance / CPU Drain** — Continuous directory-watching loops pin CPUs at 100%

### Quick Install (Claude Code)

```bash
# 1. Install the Nexus CLI
pip install ice-nexus

# 2. Start the daemon (runs in background)
ice-nexus start

# 3. Configure Claude Code to use the MCP server
# Add to your Claude Code settings (~/claude-code/settings.json or via UI):
{
  "mcpServers": {
    "ice-nexus": {
      "command": "ice-nexus",
      "args": ["mcp"]
    }
  }
}

# 4. Restart Claude Code — Nexus is now active!
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ICE NEXUS DAEMON                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ Dynamic Port    │  │ Shared-Memory    │  │ Middle-Out    │  │
│  │ Binding         │  │ Voxel Registry   │  │ Truncation    │  │
│  │ (49152-65535)   │  │ (mmap/shm)       │  │               │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MCP Server / HTTP Proxy                     │   │
│  │  Passive interception │ Voxel pinning │ Context sync     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
    ┌─────────┐           ┌─────────┐           ┌─────────┐
    │Claude   │           │Cursor   │           │Codex    │
    │Code     │           │         │           │         │
    └─────────┘           └─────────┘           └─────────┘
```

### Configuration

```toml
# ~/.config/ice-nexus/config.toml
[daemon]
port_range = "49152-65535"
shared_memory_size = "512MB"

[mcp]
enabled = true
bind_address = "127.0.0.1"

[storage]
backend = "duckdb"  # or "postgres" for cluster
path = "~/.ice/nexus.db"
```

### Verification

```bash
# Check daemon status
ice-nexus status

# View connected agents
ice-nexus agents list

# Test memory sync
ice-nexus test-sync
```

---

## 📜 License

This project has a **dual-license** structure:

| Tier | License | Scope |
|------|---------|-------|
| **OSS Core** | ![MIT](https://img.shields.io/badge/License-MIT-yellow.svg) | `ice/` wrapper, DuckDB backend, Nexus plugin |
| **Community** | ![BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-blue.svg) | PostgreSQL backend, horizontal scaling, admin dashboard |
| **Enterprise** | Proprietary | Multi-tenant RBAC, compliance engine, SLA |

- **OSS (MIT):** Free for any use, including commercial. See [LICENSE](LICENSE).
- **Community (BSL-1.1):** Source available, converts to Apache-2.0 after 4 years. See [LICENSE-COMMUNITY](LICENSE-COMMUNITY).
- **Enterprise:** Contact sales@dopove.com.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Checklist

- [ ] Fork the repo and create a feature branch
- [ ] Run tests: `pytest tests/ -v`
- [ ] Run lint: `ruff check . && mypy .`
- [ ] Add tests for new functionality
- [ ] Update documentation if needed
- [ ] Open a PR with a clear description

### Development Setup

```bash
# Clone and setup
git clone https://github.com/Dopove/indexless-context-engine.git
cd indexless-context-engine
pip install -e ".[dev,multimodal]"

# Run tests
pytest tests/ -v

# Run benchmarks
PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20
```

---

## 🔗 Links

- **Documentation:** [https://docs.dopove.com/ice](https://docs.dopove.com/ice)
- **Benchmarks:** [benchmarks/marketing/BENCHMARKS.md](benchmarks/marketing/BENCHMARKS.md)
- **Nexus Plugin Docs:** [ice_nexus/README.md](ice_nexus/README.md)
- **Issues:** [GitHub Issues](https://github.com/Dopove/indexless-context-engine/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Dopove/indexless-context-engine/discussions)

---

*Built with ❤️ by the [Dopove](https://dopove.com) team.*
