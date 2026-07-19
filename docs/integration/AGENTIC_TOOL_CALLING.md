# 🛠️ Advanced Agentic Tool Calling & MCP Integration

The Infinite Context Engine (ICE) is natively designed to support highly autonomous agents that require access to dozens of tools, external APIs, and the **Model Context Protocol (MCP)**.

Unlike standard LLM APIs where tool definitions eat into your token budget and "Agentic Amnesia" causes bots to forget previous tool results, ICE solves these problems mathematically.

---

## 1. The "Agentic Amnesia" Problem (Solved)

When an agent executes a multi-step plan (e.g., 1. Search DB -> 2. Read File -> 3. Execute Code), it generates a long history of `tool_calls` and `tool_results`. In standard SDKs, this history quickly overflows the context window, causing the agent to forget the result of step 1 by the time it reaches step 3.

**The ICE Solution:**
ICE automatically detects `role: "tool"` messages and uses its `ContextPager` to **pin** the most recent critical tool results into the active context window, while safely archiving older tool results into the Semantic Ledger (PostgreSQL). If the agent needs an old tool result later, ICE retrieves it via Deep Memory (RAG).

---

## 2. Transparent Protocol Switch (Parsing)

ICE provides a sophisticated context pipeline for autonomous agents. You do not need to learn a new tool-calling syntax. ICE perfectly parses and supports the native tool-calling formats of:

*   **OpenAI** (`tools`, `tool_choice`, `tool_calls`)
*   **Anthropic** (`tools`, `tool_choice`, `<functionCall>` XML tags)
*   **Gemini** (`tools`, `functionDeclarations`)

When the upstream LLM decides to call a tool, ICE instantly detects the syntax, **halts its internal recursive stitching engine**, and cleanly returns the exact JSON or XML tool call back to your client application.

### Example: Standard Tool Call (Python)
```python
response = await ice_client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Get the weather in Tokyo."}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather.",
            "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
        }
    }],
    x_session_id="agent-thread",
    x_user_id="user-1"
)

# ICE safely halts and returns the tool call
print(response.choices[0].message.tool_calls[0].function.arguments) 
# {"location": "Tokyo"}
```

---

## 3. Model Context Protocol (MCP) Integration

The **Model Context Protocol (MCP)** is an open standard that allows AI models to securely connect to local or remote data sources and tools. 

Because ICE maintains infinite memory, it is the perfect substrate for MCP servers. An ICE Agent can connect to 50 different MCP servers simultaneously without overflowing its context window with tool definitions.

### How ICE Handles MCP
1.  **Tool Discovery:** Your client application connects to an MCP Server (e.g., a local GitHub MCP server) and retrieves its available tools.
2.  **Pass to ICE:** You pass these tool definitions to ICE in the standard `tools` array.
3.  **Execution & Pinning:** When the agent calls an MCP tool, ICE returns the call. Your client executes the MCP tool and passes the result back. ICE permanently pins that result into the 100B Token Horizon.

### Example: MCP Integration Flow (Node.js Concept)
```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { IceClient } from "@ICE Core Team/ice-engine";

// 1. Connect to a local MCP Server (e.g., filesystem access)
const mcpClient = new Client(...);
await mcpClient.connect(...);

// 2. Get tools from MCP
const mcpTools = await mcpClient.listTools();
const iceTools = mcpTools.tools.map(t => formatForIce(t));

// 3. Ask ICE to perform a task using MCP tools
const response = await ice.chat.completions.create({
    model: "claude-3-5-sonnet",
    messages: [{ role: "user", content: "Read the README.md file." }],
    tools: iceTools,
    sessionId: "mcp-agent-01"
});

// 4. ICE returns the tool call; Client executes via MCP
if (response.choices[0].message.tool_calls) {
    const result = await mcpClient.callTool({
        name: response.choices[0].message.tool_calls[0].function.name,
        arguments: JSON.parse(response.choices[0].message.tool_calls[0].function.arguments)
    });
    
    // 5. Pass the MCP result back to ICE for infinite memory storage
    await ice.chat.completions.create({
        model: "claude-3-5-sonnet",
        messages: [
            { role: "assistant", content: null, tool_calls: response.choices[0].message.tool_calls },
            { role: "tool", name: "read_file", content: JSON.stringify(result.content) }
        ],
        sessionId: "mcp-agent-01"
    });
}
```

---

## 🎓 Demonstrations
Check the `client_demos/` folder for executable code examples:
*   **Python**: `client_demos/python/07_advanced_tool_calling.py` & `client_demos/python/08_mcp_integration.py`
*   **Node.js**: `client_demos/node/06_advanced_tool_calling.ts` & `client_demos/node/07_mcp_integration.ts`
