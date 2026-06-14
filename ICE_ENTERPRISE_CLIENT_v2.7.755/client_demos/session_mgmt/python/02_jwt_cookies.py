from fastapi import FastAPI, Depends, Cookie, HTTPException
from pydantic import BaseModel
import jwt
from ice.sdk import init, get_client
import uvicorn

app = FastAPI(title="ICE: JWT & Cookie Session Demo")

@app.on_event("startup")
async def on_startup():
    await init(max_input_tokens=16000)

SECRET_KEY = "your-enterprise-secret-key"

class ChatRequest(BaseModel):
    message: str

def get_current_user_and_session(
    auth_token: str = Cookie(None),
    thread_cookie: str = Cookie(None)
):
    """
    Extracts the user identity from a secure JWT and the active thread
    from a separate session cookie.
    """
    if not auth_token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    
    try:
        # Decode the JWT to get the verified User ID
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        # Fallback thread if the client didn't provide a specific chat tab
        session_id = thread_cookie or "default-web-session"
        
        return user_id, session_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/web/chat")
async def secure_web_chat(
    request: ChatRequest,
    context: tuple = Depends(get_current_user_and_session)
):
    """
    Secure Web App connectivity.
    Ideal for React/Next.js frontends where headers are managed via HTTP-Only Cookies.
    """
    user_id, session_id = context
    print(f"[Web Session]: Validated JWT for {user_id}. Thread: {session_id}")
    
    response = await get_client().chat.completions.create(
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": request.message}],
        x_user_id=user_id,
        x_session_id=session_id
    )
    
    return {"reply": response.choices[0].message.content}

# Dummy endpoint to generate a test cookie
@app.get("/login")
async def login():
    token = jwt.encode({"sub": "verified-user-123"}, SECRET_KEY, algorithm="HS256")
    return {"message": "Set this token as 'auth_token' cookie", "token": token}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
