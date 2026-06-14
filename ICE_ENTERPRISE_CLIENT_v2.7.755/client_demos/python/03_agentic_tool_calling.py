import asyncio
import os
from ice.sdk import init

import sys
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def run_agentic_workflow():
    UI.header("ICE: Agentic Tool Calling & Syntax Defense Demo")
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")

    ice_client = await init(max_input_tokens=16000)
    
    user_id = "agent-ops"
    session_id = "server-maintenance-task"
    
    # 1. Define Tools (Standard OpenAI format)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_server_logs",
                "description": "Fetch recent logs from the production server.",
                "parameters": {
                    "type": "object",
                    "properties": {"lines": {"type": "integer"}},
                    "required": ["lines"]
                }
            }
        }
    ]
    
    UI.user("Check the server logs for any recent 500 errors.")
    
    # 2. First Turn: Agent decides to use a tool
    # ICE's Transparent Protocol Switch detects the JSON tool call, halts recursive generation, 
    # and safely returns the exact JSON back to the client application.
    response_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "Check the server logs for any recent 500 errors."}],
        tools=tools,
        tool_choice="auto",
        x_session_id=session_id,
        x_user_id=user_id
    )
    
    # Extract tool_calls based on dict vs object
    message_1 = response_1['choices'][0]['message'] if isinstance(response_1, dict) else response_1.choices[0].message
    tool_calls = message_1.get('tool_calls') if isinstance(message_1, dict) else getattr(message_1, 'tool_calls', None)
    
    UI.agent(f"Tool Call Request: {tool_calls}")
    
    if tool_calls:
        UI.system("Executing local function 'get_server_logs(lines=10)'...")
        tool_result = "ERROR 500: Database Connection Timeout at 14:32:00."
        
        # 3. Second Turn: Client provides the tool result
        # ICE automatically 'pins' tool results to the context pager to prevent Agentic Amnesia.
        UI.system("Sending tool result back to ICE...")
        
        # Handle formatting for dict vs obj
        assistant_message = {"role": "assistant", "content": None, "tool_calls": tool_calls} if isinstance(message_1, dict) else message_1

        response_2 = await ice_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[
                assistant_message,
                {"role": "tool", "name": "get_server_logs", "content": tool_result}
            ],
            x_session_id=session_id,
            x_user_id=user_id
        )
        
        content_2 = response_2['choices'][0]['message']['content'] if isinstance(response_2, dict) else response_2.choices[0].message.content
        UI.success(f"Final Answer: {content_2}")

if __name__ == "__main__":
    asyncio.run(run_agentic_workflow())
