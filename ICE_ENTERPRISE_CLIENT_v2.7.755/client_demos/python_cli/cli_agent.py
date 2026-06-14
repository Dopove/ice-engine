#!/usr/bin/env python3
import asyncio
import os
import sys
from typing import Optional

# 1. Import the ICE Client
from ice.sdk import init

# ==============================================================================
# CLI AGENT CONFIGURATION (e.g., Claude Code, Gemini-CLI)
# ==============================================================================
# For CLI tools, we want local parsing, fast retrieval, and persistent history
# tied to the directory they are running in.


# Bind the session to the current working directory to maintain "Workspace Memory"
# This ensures that if the developer closes the terminal and reopens it tomorrow,
# the agent remembers the context of THIS specific project.
WORKSPACE_SESSION_ID = f"cli-workspace-{os.path.abspath(os.getcwd()).replace('/', '-')}"
USER_ID = os.getenv("USER", "local-dev")

async def cli_loop():
    ice_client = await init(max_input_tokens=16000)
    print(f"🤖 ICE CLI Agent Initialized.")
    print(f"📁 Workspace Memory Bound: {WORKSPACE_SESSION_ID}")
    print("Type 'exit' to quit, or 'ingest <file>' to add local context.\n")

    while True:
        try:
            user_input = input("❯ ")
            if not user_input.strip():
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            # Handle special ingestion command for CLI
            if user_input.startswith("ingest "):
                file_path = user_input.split("ingest ", 1)[1].strip()
                if os.path.exists(file_path):
                    print(f"⏳ Ingesting {file_path} into workspace memory...")
                    await ice_client.ingest(
                        file_path=file_path, 
                        x_user_id=USER_ID, 
                        x_session_id=WORKSPACE_SESSION_ID
                    )
                    print(f"✅ {file_path} embedded successfully.")
                else:
                    print(f"❌ File not found: {file_path}")
                continue

            # 2. Infinite Context Generation
            # The CLI agent doesn't need to load a massive local vector DB.
            # It just sends the prompt, and ICE pages in the relevant workspace history.
            print("⚙️ Thinking...")
            
            # Using streaming for real-time terminal output
            stream = await ice_client.chat.completions.create(
                model="claude-3-5-sonnet", # Or "gpt-4o", "gemini-1.5-pro"
                messages=[{"role": "user", "content": user_input}],
                x_user_id=USER_ID,
                x_session_id=WORKSPACE_SESSION_ID,
                stream=True
            )
            
            sys.stdout.write("🤖 ")
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    sys.stdout.write(chunk.choices[0].delta.content)
                    sys.stdout.flush()
            print("\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(cli_loop())
