# 📚 ICE SDK Functions Reference

This document provides a comprehensive reference for all public functions and methods available in the Infinite Context Engine (ICE) SDKs for Python and Node.js.

---

## 🐍 Python SDK (`ice.sdk`)

### `await ice.sdk.init(license_key: str, **kwargs) -> InfiniteContextClient`

*   **Description:** Initializes the ICE Kernel and its core components (ContextPager, EpisodicManager, etc.) directly within your Python application process. This should be called *once* at application startup. All configuration (database URLs, LLM routing, memory physics) is passed via environment variables, which `init()` reads.
*   **Use:** The primary entry point to start the ICE Engine.
*   **Example:**
    ```python
    import asyncio
    from ice.sdk import init

    # Your application's startup logic
    async def application_startup():
        # ICE reads configuration from environment variables (e.g., DATABASE_URL, ICE_POST_COMPRESSION_LIMIT)
        ice_client = await init(license_key=os.getenv("ICE_API_KEY", "your-dev-bypass-key"))
        print("ICE Engine initialized and ready.")
        return ice_client

    # Example of calling it once
    # ice_instance = asyncio.run(application_startup())
    ```

### `ice_client.chat.completions.create(model: str, messages: List[Dict], x_session_id: str, x_user_id: str, **kwargs) -> Union[AsyncGenerator, Dict]`

*   **Description:** The primary method for interacting with LLMs with infinite memory. It is 100% API-compatible with OpenAI's `chat.completions.create`, with the addition of mandatory `x_session_id` and `x_user_id` headers. ICE will automatically retrieve relevant context from your Semantic Ledger, assemble the prompt, and manage the upstream LLM call.
*   **Use:** To send user queries to an LLM while leveraging ICE's memory capabilities.
*   **Example:**
    ```python
    # Assuming 'ice_client' is an initialized InfiniteContextClient instance
    response = await ice_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Tell me about Project Alpha."}],
        x_session_id="project-alpha-research", # Unique ID for this conversation thread
        x_user_id="dev-team-lead",             # Unique ID for the user (for data isolation)
        stream=True                            # Supports streaming responses
    )
    async for chunk in response:
        print(chunk.choices[0].delta.content, end="")
    ```

### `ice_client.ingest(uri: str, x_session_id: str, x_user_id: str, **kwargs) -> int`

*   **Description:** Ingests documents (files or directories) from various sources (local filesystem, AWS S3, Google Cloud Storage) into the Semantic Ledger. ICE handles parsing, chunking, embedding, and storage.
*   **Use:** To feed large amounts of external knowledge (PDFs, codebases, documentation) into ICE's memory for retrieval during chat interactions.
*   **Example:**
    ```python
    # Assuming 'ice_client' is an initialized InfiniteContextClient instance
    # Ingest from a local file
    await ice_client.ingest(
        uri="file:///path/to/my_document.pdf", 
        x_session_id="project-alpha-research",
        x_user_id="dev-team-lead"
    )

    # Ingest from an S3 bucket
    await ice_client.ingest(
        uri="s3://my-enterprise-bucket/project_alpha_docs/", # Ingests entire folder
        x_session_id="project-alpha-research",
        x_user_id="dev-team-lead"
    )
    print("Documents ingested successfully.")
    ```

### `ice.sdk.get_client() -> InfiniteContextClient`

*   **Description:** Retrieves the globally initialized `InfiniteContextClient` instance. Useful for FastAPI's Dependency Injection or when you need to access the singleton from different modules.
*   **Use:** To access the ICE client instance after it has been initialized once by `ice.sdk.init()`.
*   **Example:**
    ```python
    from fastapi import Depends
    from ice.sdk import get_client, InfiniteContextClient

    async def chat_route(
        user_message: str,
        ice_client: InfiniteContextClient = Depends(get_client)
    ):
        # ... use ice_client
        pass
    ```

---

## 🌐 Node.js SDK (`@ICE Core Team/ice-node`)

### `new IceClient(config: IceClientConfig)`

*   **Description:** Instantiates the Node.js ICE client. This client manages the IPC communication with the native Python ICE Kernel process. It should be instantiated *once* at application startup.
*   **Use:** The primary entry point to start the ICE Engine in a Node.js application.
*   **Example:**
    ```typescript
    import { IceClient } from '@ICE Core Team/ice-node';
    import * as process from 'process';

    // ICE reads configuration from environment variables (e.g., ICE_POST_COMPRESSION_LIMIT)
    const ice = new IceClient({ 
        licenseJwt: process.env.ICE_API_KEY || "your-dev-bypass-key" 
    });
    console.log("ICE Engine initialized and ready.");
    ```

### `ice_client.chat.completions.create(request: ChatCompletionRequest) -> Promise<ChatCompletionResponse>`

*   **Description:** The primary method for interacting with LLMs with infinite memory in Node.js. It mirrors the OpenAI API, requiring `sessionId` and `userId` for context management. This call triggers the IPC bridge to the Python kernel.
*   **Use:** To send user queries to an LLM with ICE's memory capabilities from a Node.js application.
*   **Example:**
    ```typescript
    // Assuming 'ice' is an initialized IceClient instance
    const response = await ice.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: "Tell me about Project Beta." }],
        sessionId: "project-beta-research",
        userId: "dev-ops-engineer",
        // stream: false (streaming not directly supported via spawnSync yet)
    });
    console.log(response.choices[0].message.content);
    ```

### `new SessionManager(request: any)`

*   **Description:** A utility class to simplify extracting `userId` and `sessionId` from common Node.js HTTP request objects (e.g., Express `req`, Koa `ctx`). It handles header parsing and fallback to temporary session IDs.
*   **Use:** To easily get the `userId` and `sessionId` context for an incoming web request.
*   **Example:**
    ```typescript
    import { SessionManager } from '@ICE Core Team/ice-node';
    // ... inside an Express route handler
    // const req: Request = ...

    const sessionContext = new SessionManager(req).getContext();
    const sessionId = sessionContext.sessionId; // e.g., from X-Session-Id header
    const userId = sessionContext.userId;       // e.g., from X-User-Id header or req.user.id
    ```
