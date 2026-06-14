from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
import os

from app.core.ice_config import get_ice_client
from ice.sdk import InfiniteContextClient

router = APIRouter(tags=["ICE Engine Endpoints"])

class ChatRequest(BaseModel):
    model: str = "llama3.2:3b" # Default to a common Ollama model
    messages: list[dict]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class IngestRequest(BaseModel):
    file_path: str # Path to file within ICE_UPLOAD_DIR

@router.post("/chat")
async def chat_completion(
    request: ChatRequest,
    x_user_id: str = Header(..., description="Unique ID for the end-user (e.g., Alice)"),
    x_session_id: str = Header(..., description="Unique ID for the conversation thread/project (e.g., project-titan)"),
    ice_client: InfiniteContextClient = Depends(get_ice_client)
):
    """
    Handles chat completions with Infinite Memory.
    ICE dynamically pages relevant history and RAG context into the LLM's prompt.
    """
    try:
        import json
        if request.stream:
            # For streaming responses, FastAPI needs an async generator
            async def generate_chunks():
                async for chunk in await ice_client.chat.completions.create(
                    model=request.model,
                    messages=request.messages,
                    x_user_id=x_user_id,
                    x_session_id=x_session_id,
                    stream=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    yield f"data: {json.dumps(chunk)}\n\n" # OpenAI SSE format
                yield "data: [DONE]\n\n"
            
            return Response(generate_chunks(), media_type="text/event-stream")
        else:
            response = await ice_client.chat.completions.create(
                model=request.model,
                messages=request.messages,
                x_user_id=x_user_id,
                x_session_id=x_session_id,
                stream=False,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            return json.dumps(response) # Dictionary to JSON
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ICE Chat Error: {e}")

@router.post("/ingest")
async def ingest_document_endpoint(
    request: IngestRequest,
    x_user_id: str = Header(..., description="User ID for data isolation"),
    x_session_id: str = Header(..., description="Session ID to bind the document's knowledge"),
    ice_client: InfiniteContextClient = Depends(get_ice_client)
):
    """
    Ingests a document from the configured ICE_UPLOAD_DIR into the Semantic Ledger.
    ICE handles chunking, embedding, and vector indexing automatically.
    """
    try:
        # Check if file exists within the allowed upload directory
        upload_dir = os.getenv("ICE_UPLOAD_DIR", "./uploads")
        full_file_path = os.path.join(upload_dir, os.path.basename(request.file_path))
        
        if not os.path.exists(full_file_path):
            raise HTTPException(status_code=404, detail=f"File not found or not in upload directory: {request.file_path}")

        print(f"[API]: Ingesting {full_file_path} for user {x_user_id}, session {x_session_id}")
        await ice_client.ingest(
            file_path=full_file_path,
            x_user_id=x_user_id,
            x_session_id=x_session_id
        )
        return {"status": "success", "message": f"'{request.file_path}' ingested and processed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ICE Ingestion Error: {e}")

@router.get("/config")
async def get_kernel_config(ice_client: InfiniteContextClient = Depends(get_ice_client)):
    """
    Returns the live, active configuration of the ICE Kernel.
    This is a verification endpoint to prove that custom tunables are active.
    It returns a sanitized view to protect internal infrastructure details.
    """
    safe_keys = [
        "memory_cap_gb", "max_stitch_concurrency", "retention_days", 
        "chunk_size", "chunk_overlap", "max_input_tokens", "max_tokens",
        "max_continuations", "priority_memory_limit", "reasoning_recall_limit",
        "privacy_masking", "llm_routing_strategy", "dynamic_output_budget", "default_output_tokens"
    ]
    
    sanitized_config = {k: v for k, v in ice_client.config.items() if k in safe_keys}
    return {"enterprise_tunables": sanitized_config}
