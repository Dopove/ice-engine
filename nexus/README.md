# ICE Nexus

**Cross-agent client middleware daemon — shared context & token management**

ICE Nexus solves three fundamental failures in modern developer-agent workflows:

1. **Agentic Amnesia / Token Overflows** — Standard context limits choke large file reads/tool outputs, causing "Prompt long", compaction failures, "Autocompact thrashing" loops
2. **Context Siloing / Redundancy** — Developers using different agents (Claude Code, Cursor, Codex, Aider, Zed) have completely segregated memories
3. **Severe Performance / CPU Drain** — Existing tools run continuous directory-watching loops pinning CPUs at 100%, multi-agent sessions create "Write Amplification Storm" feedback loops

---

## Architecture

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

---

## Quick Install (Claude Code)

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

---

## Configuration

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

---

## Verification

```bash
# Check daemon status
ice-nexus status

# View connected agents
ice-nexus agents list

# Test memory sync
ice-nexus test-sync
```

---

## Integration with ICE

ICE Nexus works seamlessly with the ICE memory engine. When both are running:

- **Shared episodic memory** across all connected agents
- **Automatic context injection** via ICEWrapper + Nexus MCP
- **Token-aware truncation** prevents context overflow
- **Cross-agent context sync** eliminates siloing

```python
# With both ICE and Nexus active:
from ice.wrapper import ICEWrapper
from openai import AsyncOpenAI

base_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
client = ICEWrapper(base_client)  # Automatically uses Nexus if available

# Memory now shared across all your agents!
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Remember: I prefer TypeScript"}]
)
```

---

## License

ICE Nexus is **MIT licensed** (part of the OSS tier). See [LICENSE](../LICENSE).

---

## Links

- **Main ICE Repo:** [github.com/Dopove/indexless-context-engine](https://github.com/Dopove/indexless-context-engine)
- **ICE Documentation:** [docs.dopove.com/ice](https://docs.dopove.com/ice)
- **Issues:** [GitHub Issues](https://github.com/Dopove/indexless-context-engine/issues)
