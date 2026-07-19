# 📦 Node.js SDK (@ICE Core Team/ice-node)

The Node.js SDK provides a native, high-performance interface to the Indexless Context Engine. It operates as a thin IPC (Inter-Process Communication) bridge to the core Python engine, giving your Node.js application access to indexless memory without the overhead of an HTTP server.

---

## 1. Critical Prerequisite: Python Engine Installation

The `@ICE Core Team/ice-node` package is a **bridge**, not a standalone library. It **requires** the `ice-engine` Python package to be installed and available in the environment where your Node.js application is running.

**Installation Order:**
1.  Install the Python wheel.
2.  Install the Node.js package.

```bash
# Step 1: Install the correct Python wheel for your system's architecture
pip install /path/to/dist/python/ice_community-2.7.756-cp312-cp312-manylinux2014_x86_64.whl

# Step 2: Install the Node.js package in your project
npm install /path/to/dist/node/ice-node-community-2.7.756.tgz
```

## 2. Initialization

Import and instantiate the `IceClient`, providing your Production license key.

```typescript
import { IceClient } from '@ICE Core Team/ice-node';
import * as process from 'process';

const ice = new IceClient({
    licenseJwt: process.env.ICE_API_KEY || "your-Production-license-key"
});
```

The `IceClient` will automatically find and execute the Python engine (`python3 -c 'import ice.node_bridge; import asyncio; asyncio.run(ice.node_bridge.main())'`) for each request.

## 3. Core Usage: Infinite Memory Chat

The API mirrors the Python SDK. The `create` method handles all the complexity of memory management, context paging, and IPC communication.

```typescript
async function runDemo() {
    const response = await ice.chat.completions.create({
        model: "llama3:8b", // Or any model the engine is configured to use
        messages: [{ role: "user", content: "The secret is 'Vesper-Lynd'. Remember this." }],
        
        // Session and User IDs are critical for memory isolation
        sessionId: "project-quantum-research",
        userId: "user-007"
    });

    console.log(response.choices[0].message.content);
    // Expected: "Acknowledged. I have stored that information."

    // ... hours later, in a new process ...

    const recallResponse = await ice.chat.completions.create({
        model: "llama3:8b",
        messages: [{ role: "user", content: "What was the secret I told you earlier?" }],
        sessionId: "project-quantum-research", // Same session ID
        userId: "user-007"
    });

    console.log(recallResponse.choices[0].message.content);
    // Expected: "The secret you mentioned is 'Vesper-Lynd'."
}

runDemo();
```

## 4. Troubleshooting

*   **`[ICE Python Bridge Execution Error] Failed to start Python process...`**: This error means the Node.js SDK could not find `python3` in the system's `PATH` or the `ice-engine` Python package is not installed correctly in that Python environment. Verify your `pip` installation and `PATH`. You can also specify a direct path to the Python executable by setting the `ICE_PYTHON_EXECUTABLE` environment variable.
*   **`[ICE Python Bridge Error] ModuleNotFoundError: No module named 'ice'`**: This confirms the `ice-engine` Python package is not installed in the Python environment being used by the `python3` command.
