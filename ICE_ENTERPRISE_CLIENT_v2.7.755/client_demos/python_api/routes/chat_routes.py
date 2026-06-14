from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

# 1. Import the Singleton Kernel from the core configuration!
from api.core.ice_config import get_ice
from ice.sdk import InfiniteContextClient

router = APIRouter(prefix="/api/v1")

class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4o"

@router.post("/chat")
async def infinite_chat(
    request: ChatRequest,
    x_user_id: str = Header(..., description="Unique ID for the end-user"),
    x_session_id: str = Header(..., description="Unique ID for the conversation thread"),
    ice: InfiniteContextClient = Depends(get_ice) # Dependency Injection
):
    """
    Handles chat requests using the Infinite Context Engine.
    Feature developers don't need to load DBs or manage context windows.
    They just pass the user ID, session ID, and the prompt. ICE does the rest.
    """
    try:
        # ICE automatically fetches historical data, applies Deep Memory (RAG), 
        # injects Reasoning Traces, and dynamically scales the token budget.
        response = await ice.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": request.message}],
            x_user_id=x_user_id,
            x_session_id=x_session_id
        )
        
        return {
            "status": "success",
            "reply": response.choices[0].message.content,
            "session": x_session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest_document(
    file_path: str,
    x_user_id: str = Header(...),
    x_session_id: str = Header(...),
    ice: InfiniteContextClient = Depends(get_ice)
):
    """
    Ingests a massive document (e.g., a 1000-page PDF) directly into the user's session.
    """
    await ice.ingest(file_path=file_path, x_user_id=x_user_id, x_session_id=x_session_id)
    return {"status": "success", "message": f"File {file_path} successfully embedded into the 100B Horizon."}
