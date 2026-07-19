# 🧠 Infinite Memory & Context Management

Unlike standard LLMs that "forget" previous instructions when the conversation exceeds 8,192 tokens, the Indexless Context Engine (ICE) provides a **100-Billion Token Horizon**.

You do not need to manually append previous messages to an array or build your own vector database. ICE handles the memory paging automatically.

---

## The Core Concept: Session IDs

To use indexless memory, you only need to provide one mandatory header: `X-Session-Id`.

ICE treats a "Session" as a chronological thread (e.g., a specific coding project, a long-form story, or a specific customer support ticket). ICE permanently records all messages sent with the same Session ID and automatically pages them back into the LLM's active context window when relevant.

### Example: Storing a Memory

Send a message establishing a fact.

**Python (Native)**
```python
response = await ice.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "My secret password is 'DELTA-9'."}],
    x_session_id="project-alpha"
)
```

**Node.js (Thin Client)**
```javascript
const response = await ice.chat.completions.create({
    model: "claude-3-5-sonnet",
    messages: [{ role: "user", content: "My secret password is 'DELTA-9'." }],
    sessionId: "project-alpha"
});
```



### Example: Retrieving a Memory (Hours or Months Later)

Send a new request using the **same Session ID**. You do not need to send the previous messages in the array. ICE will find the relevant memory and inject it into the LLM's prompt in `<100ms`.

**Python (Native)**
```python
response = await ice.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What was my secret password?"}],
    x_session_id="project-alpha" # Uses the same session
)
# Output: "Your secret password is 'DELTA-9'."
```



---

## Best Practices for Memory Paging

1.  **Unique Sessions per Project:** Do not reuse the same `X-Session-Id` for every request. If a user is working on "Project A" and "Project B", use two different IDs (e.g., `session_A` and `session_B`). This prevents the LLM from accidentally retrieving code from Project A when the user is asking about Project B.
2.  **System Prompts:** If you pass a `{"role": "system"}` message, ICE permanently locks it to the "Floor" of the context window. It will never be truncated or forgotten, no matter how long the conversation gets.
3.  **User Identification:** If your application supports multiple users, you **must** also pass the `X-User-Id` header to ensure absolute cryptographic data isolation (see the [Multi-Tenant Isolation Guide](multi_tenant_isolation.md)).