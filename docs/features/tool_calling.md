# 🛠️ Agentic Tool Calling & JSON Paging

ICE acts as a sophisticated context pipeline for complex autonomous agents. It supports native tool calling structures for OpenAI, Anthropic, and Gemini.

More importantly, ICE solves **"Agentic Amnesia."** When an agent executes a 50-step plan, the massive JSON history of `tool_calls` and `tool_results` usually blows out the context window. ICE intelligently pins recent tool results to the prompt and archives older results to the Semantic Ledger, guaranteeing infinite autonomous execution.

---

## How to Execute a Tool Call

Pass tools to the ICE Engine exactly as you would to the standard OpenAI API.

### 1. The Agent Requests a Tool

**Python**
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather.",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
    }
}]

response = await ice.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=tools,
    x_session_id="agent-task-01"
)

# ICE detects the JSON payload, halts recursive generation, and returns the tool call natively.
tool_call = response.choices[0].message.tool_calls[0]
print(tool_call.function.arguments) # {"location": "Tokyo"}
```

### 2. The Client Provides the Tool Result

Once your application executes the local tool (e.g., hitting a weather API), you return the result to ICE using the standard `{"role": "tool"}` format. 

**ICE permanently pins this result into the `X-Session-Id`'s indexless memory.**

**Python**
```python
# Your app hits the weather API...
weather_data = '{"temp": "22C", "condition": "Sunny"}'

# Send the result back to ICE
response = await ice.chat.completions.create(
    model="gpt-4o",
    messages=[
        # You must include the original tool_call that ICE requested
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        # And the result of your local execution
        {"role": "tool", "name": "get_weather", "content": weather_data}
    ],
    tools=tools,
    x_session_id="agent-task-01" # MUST be the same session
)

print(response.choices[0].message.content)
# Result: "The weather in Tokyo is currently Sunny and 22 degrees Celsius."
```

---

## Integration with Model Context Protocol (MCP)

ICE's indexless memory makes it the perfect substrate for MCP Servers. Because ICE stores the results of tool calls permanently, an agent can use an MCP server to read a 10,000-line file, and ICE will chunk and store that file in the Semantic Ledger indefinitely.

### Architecture Flow

1.  **Discover:** Your client application connects to a local MCP Server (e.g., `mcp_github`) and retrieves the available tools.
2.  **Context Injection:** You pass the `mcpTools` array to ICE in the `tools` parameter.
3.  **Execute:** ICE decides to use an MCP tool and returns the payload to your client.
4.  **Pin:** Your client executes the tool via the MCP protocol and passes the raw result back to ICE using `{"role": "tool"}`. ICE commits the MCP output to the 100B Token Horizon.

*(See the `client_demos/python/08_mcp_integration.py` file in your distribution for a complete executable MCP mock.)*