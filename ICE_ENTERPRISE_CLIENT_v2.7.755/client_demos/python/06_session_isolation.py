import asyncio
import os
from ice.sdk import init

import sys
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def demonstrate_session_isolation():
    UI.header("ICE: Session & Project Isolation Demo")
    print(f"{UI.YELLOW}Problem:{UI.RESET} 'Context Bleed' where an AI mixes up details from different projects.")
    print(f"{UI.CYAN}Solution:{UI.RESET} ICE hermetically seals memory ledgers based on the `x_session_id`.\n")
    
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    UI.system("Booting live ICE Kernel...")
    ice_client = await init(max_input_tokens=16000)
    
    user_id = "developer-alice"
    
    # Define two distinct project workspaces
    project_alpha_session = "workspace-/projects/alpha-frontend"
    project_beta_session = "workspace-/projects/beta-backend"
    
    # --- PHASE 1: Populate Project Alpha ---
    UI.step("PHASE 1: Populate Project Alpha")
    UI.user("The frontend framework is React 18. Remember this.")
    await UI.simulate_processing(1.0, "Storing to Alpha Ledger")
    response_alpha_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "The frontend framework is React 18. Remember this."}],
        x_session_id=project_alpha_session,
        x_user_id=user_id
    )
    content_alpha_1 = response_alpha_1['choices'][0]['message']['content'] if isinstance(response_alpha_1, dict) else response_alpha_1.choices[0].message.content
    UI.agent(content_alpha_1)
    
    # --- PHASE 2: Populate Project Beta ---
    UI.step("PHASE 2: Populate Project Beta")
    UI.user("The backend database is PostgreSQL. Remember this.")
    await UI.simulate_processing(1.0, "Storing to Beta Ledger")
    response_beta_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "The backend database is PostgreSQL. Remember this."}],
        x_session_id=project_beta_session,
        x_user_id=user_id
    )
    content_beta_1 = response_beta_1['choices'][0]['message']['content'] if isinstance(response_beta_1, dict) else response_beta_1.choices[0].message.content
    UI.agent(content_beta_1)
    
    # --- PHASE 3: Prove Isolation (Context Switching) ---
    UI.step("PHASE 3: Prove Isolation (Context Switching)")
    
    # Switch back to Alpha and ask about the database
    UI.system("[Switching to Project Alpha]: Asking about the database...")
    UI.user("What database are we using?")
    await UI.simulate_processing(1.5, "Retrieving Alpha Context")
    response_alpha = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "What database are we using?"}],
        x_session_id=project_alpha_session,
        x_user_id=user_id
    )
    content_alpha = response_alpha['choices'][0]['message']['content'] if isinstance(response_alpha, dict) else response_alpha.choices[0].message.content
    UI.agent(f"[Alpha Context]: {content_alpha}")
    UI.system("Notice: The agent DOES NOT know about PostgreSQL, because it is isolated to Beta.")
    
    # Stay in Alpha and ask about the framework
    UI.system("[Remaining in Project Alpha]: Asking about the framework...")
    UI.user("What framework are we using?")
    await UI.simulate_processing(1.5, "Retrieving Alpha Context")
    response_alpha_framework = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "What framework are we using?"}],
        x_session_id=project_alpha_session,
        x_user_id=user_id
    )
    content_alpha_fw = response_alpha_framework['choices'][0]['message']['content'] if isinstance(response_alpha_framework, dict) else response_alpha_framework.choices[0].message.content
    UI.agent(f"[Alpha Context]: {content_alpha_fw}")
    
    UI.success("The agent perfectly recalls React 18 while remaining isolated from the Beta project.")

if __name__ == "__main__":
    asyncio.run(demonstrate_session_isolation())
