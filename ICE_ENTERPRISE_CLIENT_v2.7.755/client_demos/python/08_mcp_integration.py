import asyncio
import json
from ice.sdk import init
import sys
import os
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def demonstrate_mcp_integration():
    UI.header("ICE: Model Context Protocol (MCP) Integration Demo")
    print("This demo simulates how ICE interacts with an MCP Server.")
    print("Because ICE has infinite memory, it can handle thousands of MCP tool results.")
    
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    UI.system("Booting live ICE Kernel...")
    ice_client = await init(max_input_tokens=16000)
    
    session_id = "mcp-workspace-01"
    user_id = "developer-bob"
    
    # 1. Simulate fetching tools from an MCP Server (e.g., a local GitHub MCP)
    UI.system("Discovering tools from local MCP Server (Github-MCP)...")
    mcp_tools = [
        {
            "type": "function",
            "function": {
                "name": "mcp_github_read_file",
                "description": "Read a file from a GitHub repository.",
                "parameters": {"type": "object", "properties": {"repo": {"type": "string"}, "path": {"type": "string"}}, "required": ["repo", "path"]}
            }
        }
    ]
    UI.system(f"Found tool: {mcp_tools[0]['function']['name']}")
    
    # 2. Ask ICE to perform a task using the MCP tool
    UI.user("Read the 'main.py' file from 'dopove/ice-core'.")
    await UI.simulate_processing()
    response_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "Read the 'main.py' file from 'dopove/ice-core'."}],
        tools=mcp_tools,
        x_session_id=session_id,
        x_user_id=user_id
    )
    
    message_1 = response_1['choices'][0]['message'] if isinstance(response_1, dict) else response_1.choices[0].message
    tool_calls = message_1.get('tool_calls') if isinstance(message_1, dict) else getattr(message_1, 'tool_calls', None)
    
    # 3. Execute the MCP Tool
    if tool_calls and tool_calls[0]['function']['name'] == "mcp_github_read_file":
        args = json.loads(tool_calls[0]['function']['arguments'])
        UI.agent(f"Calling MCP Tool '{tool_calls[0]['function']['name']}' with {args}")
        
        # Simulate the actual MCP execution over stdio or SSE
        UI.system("Executing via MCP Client...")
        await asyncio.sleep(1) # Simulate network delay
        mcp_result = '{"content": "def main():\\n    print(\'Hello ICE\')\\n"}'
        UI.system("MCP Server returned file content.")
        
        # 4. Pass the MCP result back to ICE
        UI.system("Pushing MCP result into ICE's Infinite Memory Horizon...")
        await UI.simulate_processing()
        
        assistant_message = {"role": "assistant", "content": None, "tool_calls": tool_calls} if isinstance(message_1, dict) else message_1

        response_2 = await ice_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[
                assistant_message,
                {"role": "tool", "tool_call_id": tool_calls[0]['id'], "name": "mcp_github_read_file", "content": mcp_result}
            ],
            tools=mcp_tools,
            x_session_id=session_id,
            x_user_id=user_id
        )
        
        content_2 = response_2['choices'][0]['message']['content'] if isinstance(response_2, dict) else response_2.choices[0].message.content
        UI.agent(f"Final Answer: {content_2}")
        UI.success("MCP Integration Successful")

if __name__ == "__main__":
    asyncio.run(demonstrate_mcp_integration())