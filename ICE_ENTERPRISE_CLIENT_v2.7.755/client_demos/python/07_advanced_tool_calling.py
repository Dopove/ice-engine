import asyncio
import json
from ice.sdk import init
import sys
import os
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def demonstrate_advanced_tools():
    UI.header("ICE: Advanced Agentic Tool Calling Demo")
    print(f"This demo proves ICE can handle multiple tools, parse arguments flawlessly,")
    print(f"and prevent 'Agentic Amnesia' by pinning tool results.\n")
    
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    UI.system("Booting live ICE Kernel...")
    ice_client = await init(max_input_tokens=16000)

    session_id = "complex-agent-task-001"
    user_id = "admin-bot"
    
    tools = [
        {"type": "function", "function": {"name": "search_database", "description": "Search", "parameters": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}},
        {"type": "function", "function": {"name": "reset_password", "description": "Reset", "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}}}
    ]
    
    UI.step("TURN 1: The Request")
    UI.user("Find the user 'alex@example.com' and reset their password.")
    await UI.simulate_processing(1.5, "Agent Reasoning")
    response_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "Find the user 'alex@example.com' and reset their password."}],
        tools=tools,
        x_session_id=session_id,
        x_user_id=user_id
    )
    
    message_1 = response_1['choices'][0]['message'] if isinstance(response_1, dict) else response_1.choices[0].message
    tool_calls = message_1.get('tool_calls') if isinstance(message_1, dict) else getattr(message_1, 'tool_calls', None)
    
    if tool_calls and tool_calls[0]['function']['name'] == "search_database":
        args = json.loads(tool_calls[0]['function']['arguments'])
        UI.agent(f"I need to call 'search_database' with {args}")
        
        UI.step("TURN 2: Tool Execution (Search)")
        UI.system("Executing search_database...")
        await UI.simulate_processing(1.0, "Searching DB")
        db_result = '{"user_id": "U-9942", "status": "active"}'
        UI.system("Returning database result to ICE. Notice how ICE seamlessly parses the ongoing thread.")
        
        await UI.simulate_processing(1.5, "Agent Reasoning")
        
        assistant_message = {"role": "assistant", "content": None, "tool_calls": tool_calls} if isinstance(message_1, dict) else message_1

        response_2 = await ice_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[
                assistant_message,
                {"role": "tool", "tool_call_id": tool_calls[0]['id'], "name": "search_database", "content": db_result},
            ],
            tools=tools,
            x_session_id=session_id,
            x_user_id=user_id
        )
        
        message_2 = response_2['choices'][0]['message'] if isinstance(response_2, dict) else response_2.choices[0].message
        tool_calls_2 = message_2.get('tool_calls') if isinstance(message_2, dict) else getattr(message_2, 'tool_calls', None)
        
        if tool_calls_2 and tool_calls_2[0]['function']['name'] == "reset_password":
            args_2 = json.loads(tool_calls_2[0]['function']['arguments'])
            UI.agent(f"Now I need to call 'reset_password' with {args_2}")
            
            UI.step("TURN 3: Tool Execution (Reset)")
            UI.system("Executing reset_password...")
            await UI.simulate_processing(1.0, "Sending Email")
            reset_result = '{"status": "success", "email_sent": true}'
            
            await UI.simulate_processing(1.5, "Agent Synthesizing")
            
            assistant_message_2 = {"role": "assistant", "content": None, "tool_calls": tool_calls_2} if isinstance(message_2, dict) else message_2

            response_3 = await ice_client.chat.completions.create(
                model="llama3.2:3b",
                messages=[
                    assistant_message_2,
                    {"role": "tool", "tool_call_id": tool_calls_2[0]['id'], "name": "reset_password", "content": reset_result},
                ],
                tools=tools,
                x_session_id=session_id,
                x_user_id=user_id
            )
            
            content_3 = response_3['choices'][0]['message']['content'] if isinstance(response_3, dict) else response_3.choices[0].message.content
            UI.agent(f"Final Answer: {content_3}")
            UI.success("ICE managed a multi-step tool chain and retained context across turns.")

if __name__ == "__main__":
    asyncio.run(demonstrate_advanced_tools())