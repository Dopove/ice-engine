import asyncio
import websockets
import json

async def test_ice_websocket():
    uri = "ws://localhost:8080/v1/ws/chat"
    
    payload = {
        "session_id": "ws-reasoning-test",
        "tenant_id": "823dc24a-885e-4586-a74b-9144dcc0f849",
        "model": "ministral-3:3b",
        "messages": [
            {"role": "user", "content": "Please explain the relationship between entropy and the arrow of time. Wrap your internal deliberation in <thought> tags."}
        ]
    }
    
    print(f"Connecting to ICE WebSocket at {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Sending payload...")
            await websocket.send(json.dumps(payload))
            
            print("Waiting for streaming response...")
            async for message in websocket:
                try:
                    # OpenAI streaming format often starts with 'data: '
                    if message.startswith("data: "):
                        data_str = message[6:]
                        if data_str.strip() == "[DONE]":
                            print("\n[DONE]")
                            break
                        
                        data = json.loads(data_str)
                        content = data['choices'][0]['delta'].get('content', '')
                        print(content, end="", flush=True)
                except Exception as e:
                    print(f"\nError parsing message: {e}")
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ice_websocket())
