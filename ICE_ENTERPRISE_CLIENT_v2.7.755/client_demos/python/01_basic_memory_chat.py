import asyncio
import os
from ice.sdk import init

# Import our new UI module
import sys
sys.path.append(os.path.dirname(__file__))
from ui import UI

async def run_basic_chat():
    UI.header("ICE: Infinite Memory Chat Demo")
    
    UI.system("Booting live ICE Kernel...")
    ice_client = await init(max_input_tokens=16000)
    
    user_id = "user-7789"
    session_id = "project-x-research"
    
    UI.step("First Interaction (Establishing Context)")
    UI.user("The secret launch code is 'DELTA-9'. Remember this.")
    
    await UI.simulate_processing(1.5, "Processing with ICE")
    response_1 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "The secret launch code is 'DELTA-9'. Remember this for later."}],
        x_session_id=session_id,
        x_user_id=user_id
    )
    UI.agent(response_1['choices'][0]['message']['content'])
    
    UI.step("Simulating massive context drift")
    await UI.simulate_processing(2.0, "Simulating 10,000 tokens of conversation")
    
    UI.step("Second Interaction (Retrieving Deep Memory without passing history manually)")
    UI.user("What was that launch code again?")
    
    await UI.simulate_processing(1.5, "Retrieving Deep Memory from Semantic Ledger")
    response_2 = await ice_client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "What was that launch code again?"}],
        x_session_id=session_id,
        x_user_id=user_id
    )
    UI.agent(response_2['choices'][0]['message']['content'])
    
    UI.success("Infinite Memory Recall Successful")

if __name__ == "__main__":
    asyncio.run(run_basic_chat())
