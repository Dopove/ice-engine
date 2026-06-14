from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ice.sdk import init, get_client
import uvicorn
import json

app = FastAPI(title="ICE: Stateful WebSocket Demo")

@app.on_event("startup")
async def on_startup():
    await init(max_input_tokens=16000)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Stateful WebSocket connectivity.
    Ideal for real-time streaming, voice agents, and persistent connections.
    """
    # 1. Accept the connection
    await websocket.accept()
    
    # 2. Handshake Phase: The client MUST send their authentication and session intent first.
    try:
        handshake_raw = await websocket.receive_text()
        handshake = json.loads(handshake_raw)
        
        user_id = handshake.get("user_id")
        session_id = handshake.get("session_id")
        
        if not user_id or not session_id:
            await websocket.send_text("ERROR: Missing user_id or session_id in handshake.")
            await websocket.close(code=1008)
            return
            
        print(f"[WebSocket Opened]: User {user_id} bound to Thread {session_id}")
        await websocket.send_text("SYSTEM: Handshake successful. Infinite Context established.")
        
    except Exception as e:
        print(f"Handshake failed: {e}")
        await websocket.close(code=1008)
        return

    # 3. Persistent Inference Loop
    # The socket remains open. The developer doesn't need to re-pass the session ID.
    try:
        while True:
            # Wait for client message
            user_message = await websocket.receive_text()
            print(f"[Received]: {user_message}")
            
            # Fire the request into ICE. Notice `stream=True`!
            stream = await get_client().chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": user_message}],
                x_user_id=user_id,
                x_session_id=session_id,
                stream=True  # ICE streams the tokens back immediately
            )
            
            # 4. Stream tokens directly to the client as they arrive from the upstream LLM
            # This provides ultra-low latency UX for voice or chat apps.
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    await websocket.send_text(chunk.choices[0].delta.content)
            
            # Send a delimiter so the frontend knows the ICE turn is complete
            await websocket.send_text("[DONE]")
            
    except WebSocketDisconnect:
        print(f"[WebSocket Closed]: Thread {session_id} disconnected cleanly.")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)
