import asyncio
import websockets
import json
import uuid

import pytest

@pytest.mark.skip(reason="Networking dependent test")
async def test_reasoning_multi_turn():
    uri = "ws://localhost:8081/v1/ws/chat"
    session_id = f"multi-turn-{uuid.uuid4().hex[:8]}"
    tenant_id = "823dc24a-885e-4586-a74b-9144dcc0f849"
    
    print(f"Starting Multi-turn Reasoning Test (Session: {session_id})")
    
    async with websockets.connect(uri) as websocket:
        # --- Turn 1: Establish Reasoning ---
        print("\n--- Turn 1: Establishing reasoning trace ---")
        payload1 = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "model": "llama3.2:latest",
            "messages": [
                {"role": "user", "content": "SYSTEM: You MUST start your response with a thinking block wrapped in [think] and [/think] tags. Deliberate deeply about the engineering challenges of a solar-powered car. Then provide your final answer."}
            ]
        }
        await websocket.send(json.dumps(payload1))
        
        full_response1 = ""
        print("Turn 1 Response:")
        while True:
            try:
                msg = await websocket.recv()
                if msg.startswith("data: "):
                    data_str = msg[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    content = chunk['choices'][0]['delta'].get('content', '')
                    full_response1 += content
                    print(content, end="", flush=True)
            except Exception as e:
                print(f"\nTurn 1 Error: {e}")
                break
        
        print("\nTurn 1 Complete. Full response received.")
        
        # Give a small delay for DB persistence
        await asyncio.sleep(2)
        
        # --- Turn 2: Verify Persistence ---
        print("\n--- Turn 2: Verifying persistence ---")
        payload2 = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "model": "llama3.2:latest",
            "messages": [
                {"role": "user", "content": "Now, based on your previous internal deliberation, what is the single most critical safety protocol we should implement?"}
            ]
        }
        await websocket.send(json.dumps(payload2))
        
        full_response2 = ""
        print("Response 2 (should reference Turn 1 reasoning):")
        while True:
            try:
                msg = await websocket.recv()
                if msg.startswith("data: "):
                    data_str = msg[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    content = chunk['choices'][0]['delta'].get('content', '')
                    full_response2 += content
                    print(content, end="", flush=True)
            except Exception as e:
                print(f"\nTurn 2 Error: {e}")
                break
        
        print("\n\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(test_reasoning_multi_turn())
