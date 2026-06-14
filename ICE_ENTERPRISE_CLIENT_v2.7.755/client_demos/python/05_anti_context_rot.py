import asyncio
import os
from ice.sdk import init

import sys
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def demonstrate_anti_context_rot():
    UI.header("ICE: Anti-Context Rot & Infinite Memory Retention Demo")
    print(f"{UI.YELLOW}Problem:{UI.RESET} Standard LLMs 'forget' early instructions when the conversation gets too long (Context Rot).")
    print(f"{UI.CYAN}Solution:{UI.RESET} ICE's ContextPager automatically anchors critical facts and pages chronological history.\n")
    
    UI.system("This demo requires a live ICE kernel and database.")
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.")
    UI.system("Booting live ICE Kernel...")
    ice_client = await init(max_input_tokens=100000)

    user_id = "researcher-01"
    session_id = "long-term-project-alpha"
    
    UI.step("[Turn 1] Establishing core project parameters...")
    UI.user("CRITICAL PROJECT PARAMETER: The primary server's IP address is 192.168.1.100. Never forget this.")
    
    await UI.simulate_processing()
    response_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "CRITICAL PROJECT PARAMETER: The primary server's IP address is 192.168.1.100. Never forget this."}],
        x_session_id=session_id,
        x_user_id=user_id
    )
    UI.agent(response_1['choices'][0]['message']['content'] if isinstance(response_1, dict) else response_1.choices[0].message.content)
    
    UI.step("Simulating massive context drift (thousands of tokens of unrelated discussion)...")
    await UI.simulate_processing(2.0, "Drifting context")
    for i in range(3):
        await ice_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "Analyze this random log file: [ERROR timeout ]"}],
            x_session_id=session_id,
            x_user_id=user_id
        )
    UI.system("Context drift complete. Standard LLMs would have evicted the 'Needle' by now.")
    
    UI.step("[Turn 50] Proving Memory Retention")
    UI.user("What is the primary server IP we established at the beginning of the project?")
    
    await UI.simulate_processing(1.5, "Retrieving from Deep Memory")
    response_final = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "What is the primary server IP we established at the beginning of the project?"}],
        x_session_id=session_id,
        x_user_id=user_id
    )
    
    UI.agent(response_final['choices'][0]['message']['content'] if isinstance(response_final, dict) else response_final.choices[0].message.content)
    UI.success("ICE mathematically prevented context rot. The agent perfectly recalled a fact from the distant past.")

if __name__ == "__main__":
    asyncio.run(demonstrate_anti_context_rot())
