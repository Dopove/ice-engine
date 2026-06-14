from fastapi import FastAPI, Header, Depends
from pydantic import BaseModel
from ice.sdk import init, get_client
import uvicorn

app = FastAPI(title="ICE: HTTP Header Session Demo")

@app.on_event("startup")
async def on_startup():
    await init(max_input_tokens=16000)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    # 1. Standard API Key extraction
    authorization: str = Header(..., description="Bearer <token>"),
    
    # 2. Explicit Session Binding (The ICE Standard)
    # The client passes the session thread ID in the headers
    x_session_id: str = Header(..., description="Unique Thread ID"),
    
    # 3. User Identity Binding
    # Prevents cross-tenant data leakage in the Semantic Ledger
    x_user_id: str = Header("default-user", description="Unique User ID")
):
    """
    Standard Stateless HTTP connectivity.
    The most common integration pattern for mobile apps and REST APIs.
    """
    print(f"[Session]: User: {x_user_id} | Thread: {x_session_id}")
    
    # ICE processes the stateless request, loads the history for `x_session_id`,
    # generates the response, and immediately saves it back to the database.
    response = await get_client().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": request.message}],
        x_user_id=x_user_id,
        x_session_id=x_session_id
    )
    
    return {"reply": response.choices[0].message.content}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
