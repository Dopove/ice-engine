import asyncio
import os
from ice.sdk import init
from ui import UI # Assuming UI helper is in the same directory

async def run_multimodal_ingest():
    UI.header("ICE: Multimodal Ingestion Demo")
    
    # Create a dummy file for ingestion
    file_path = "./sample_architecture_diagram.txt"
    with open(file_path, "w") as f:
        f.write("The architecture consists of a Node.js engine and a Python physics engine.")
            
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    
    ice_client = await init(max_input_tokens=16000)
    
    user_id = "user-7789"
    session_id = "project-x-research"
    
    # 2. One-Line Ingestion
    print(f"\n[System]: Ingesting {file_path} into the 100B Token Horizon...")
    await ice_client.ingest(
        file_path=file_path,
        session_id=session_id,
        x_user_id=user_id
    )
    print("[System]: Ingestion complete. Knowledge is now permanently available.")
    
    # 3. Query the ingested knowledge
    print("\n[User]: Summarize the architecture diagram on page 2.")
    response = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "Summarize the architecture diagram on page 2."}],
        x_session_id=session_id,
        x_user_id=user_id
    )
    
    # Handle dict vs object access depending on if it's the mock or real response
    content = response['choices'][0]['message']['content'] if isinstance(response, dict) else response.choices[0].message.content
    print(f"[ICE Agent]: {content}")

    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

if __name__ == "__main__":
    asyncio.run(run_multimodal_ingest())
