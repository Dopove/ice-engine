# 🔌 ICE Libraries & Integration

ICE provides native libraries to make interacting with the Infinite Context Engine frictionless. 

If you are using a language without a native ICE SDK, you can use any standard OpenAI-compatible client.

---

## 🐍 Python SDK (`ice.sdk`)

The Python SDK is a native, pre-compiled library. It is designed for backend services and AI agents where you want tight, in-process integration with the ICE Kernel.

### Installation

```bash
pip install ice_engine-2.7.756-py3-none-any.whl
```

### Quickstart (Chat & Memory)

```python
import asyncio
from ice.sdk import init

async def main():
    # Initialize the ICE Kernel (Do this once at application startup)
    ice = await init(max_input_tokens=32768)

    # Any chat completion automatically inherits infinite memory
    response = await ice.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "My favorite framework is FastAPI."}],
        x_user_id="user_123",
        x_session_id="project_alpha"
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

### Document Ingestion (Multimodal)

ICE natively handles chunking and vector embedding.

```python
import asyncio
from ice.sdk import init

async def main():
    ice = await init()
    
    # Instantly ingest a PDF, Text file, or Markdown into the Semantic Ledger
    await ice.ingest(
        file_path="./architecture_spec.pdf",
        x_user_id="user_123",
        x_session_id="project_alpha"
    )
    print("Ingestion complete.")

asyncio.run(main())
```

---

## 🌐 Node.js Thin Client (`@dopove/ice-engine`)

The Node.js SDK is a lightweight TypeScript "Thin Client" that securely bridges your application to a running ICE Engine via native C++ bindings.

### Installation

```bash
npm install @dopove/ice-engine@file:./dist_node/dopove-ice-engine-2.7.756.tgz
```

### Quickstart (Express.js Example)

The Node SDK includes a `SessionManager` to automatically extract required identity headers (`x-session-id`, `x-user-id`) from standard HTTP requests.

```typescript
import express from 'express';
import { IceClient, SessionManager } from '@dopove/ice-engine';

const app = express();
app.use(express.json());

const ice = new IceClient({
    // For Enterprise builds, a valid license key is required
    licenseJwt: process.env.ICE_LICENSE_JWT!,
});

app.post('/api/chat', async (req, res) => {
    // Automatically extracts identities from req.headers
    const session = new SessionManager(req).getContext();

    try {
        const response = await ice.chat.completions.create({
            model: "claude-3-5-sonnet",
            messages: [{ role: "user", content: req.body.message }],
            sessionId: session.sessionId,
            userId: session.userId,
        });
        
        res.json({ reply: response.choices[0].message.content });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3000, () => console.log('Server running on port 3000'));
```
