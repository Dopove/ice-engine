# 📂 Workspace Mount (Local Indexer)

**The Production Solution for Massive Input Context**

When dealing with massive inputs like entire codebases (e.g., 500,000+ tokens), pasting raw text directly into a chat API request is an architectural anti-pattern. It causes HTTP payload bloat, network timeouts, and significant data exfiltration risks.

ICE solves this with the **Workspace Mount** feature.

## How It Works

Instead of sending your codebase over the network, ICE flips the architecture. You "mount" your codebase locally using the ICE CLI or SDK.

1.  **Local Processing:** ICE uses a lightweight, local ONNX runtime to chunk and vectorize your codebase directly on your machine.
2.  **Vector Streaming:** ICE streams only the highly compressed mathematical vectors (384-dimensional arrays) directly into your isolated PostgreSQL Semantic Ledger.
3.  **Instant Chat:** When your agent interacts with the LLM, the prompt payload remains tiny. ICE handles the semantic retrieval natively from the pre-populated ledger.

## CLI Usage (Recommended)

The easiest way to mount a codebase is using the ICE CLI:

```bash
ice mount ./my-massive-codebase --session-id "bug-hunt-1" --user-id "dev-team-alpha"
```

## SDK Usage

You can also trigger a workspace mount programmatically using the SDK:

### Python
```python
import asyncio
from ice.sdk import init

async def mount_codebase():
    ice = await init()
    await ice.ingest(
        uri="file://./my-massive-codebase",
        x_session_id="bug-hunt-1",
        x_user_id="dev-team-alpha"
    )

asyncio.run(mount_codebase())
```

## Security & Performance Benefits
*   **Zero Data Exfiltration:** Your raw source code never travels over the open internet to an LLM provider during the ingestion phase.
*   **No API Timeouts:** Bypasses API Gateway payload limits and HTTP timeout restrictions.
*   **O(1) Cost Scaling:** You only pay for the specific tokens ICE retrieves during the chat phase, not the entire 500k codebase on every turn.
