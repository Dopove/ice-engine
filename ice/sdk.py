import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from .kernel import ICEKernel
from .main import generate_ice_chunks, ice_server
from .telemetry import TelemetryConfig, RemoteTelemetryClient

logger = logging.getLogger("ice_sdk")

# Use a valid UUID for the native tenant to bypass validation errors in DB
NATIVE_TENANT_ID = "823dc24a-885e-4586-a74b-9144dcc0f849"

# --- GLOBAL SINGLETON STATE ---
_ice_kernel: Optional[ICEKernel] = None
_default_client: Optional['IndexlessContextClient'] = None

class ICEError(Exception):
    """Base class for all ICE SDK errors."""
    def __init__(self, message: str, code: str = "ICE_ERR_GENERIC", trace_id: str = None):
        super().__init__(message)
        self.code = code
        self.trace_id = trace_id

class IndexlessContextClient:
    """
    The High-Level Developer Interface for ICE.
    Encapsulates Kernel initialization, Multimodal Ingestion, and Completion Stitching.
    """
    def __init__(self, kernel: ICEKernel, **config_kwargs):
        self.kernel = kernel
        self.config = config_kwargs # Store all provided kwargs as configuration
        # Initialize telemetry client from kernel
        self.telemetry = kernel.telemetry

    async def health(self) -> dict:
        """Returns health status of the kernel."""
        return await self.kernel.health()

    async def shutdown(self):
        """Disconnects the ICE kernel gracefully."""
        await self.kernel.disconnect()

    async def ingest(self, file_path: str, session_id: str, x_user_id: str = "default-user", metadata: dict = None) -> int:
        """
        [DX] One-line multimodal ingestion.
        Handles parsing, chunking, and semantic indexing.
        """
        logger.info(f"ICE Ingest: Processing {file_path} for session {session_id}...")

        # 1. Use the IngestionPipeline instance from the Kernel
        num_chunks = await self.kernel.ingestion.ingest_path(
            tenant_id=NATIVE_TENANT_ID,
            user_id=x_user_id,
            path=file_path
        )

        logger.info(f"ICE Ingest: Successfully indexed {num_chunks} fragments into the indexless horizon.")
        return num_chunks

    async def _emit_telemetry(self, event_type: str, data: dict):
        """Emit telemetry event through kernel's telemetry client."""
        if hasattr(self.kernel, 'telemetry') and self.kernel.telemetry:
            await self.kernel.telemetry.emit({
                "type": event_type,
                "timestamp": time.time(),
                "data": data
            })

    async def ingest(self, file_path: str, session_id: str, x_user_id: str = "default-user", metadata: dict = None) -> int:
        """
        [DX] One-line multimodal ingestion.
        Handles parsing, chunking, and semantic indexing.
        """
        logger.info(f"ICE Ingest: Processing {file_path} for session {session_id}...")

        # 1. Use the IngestionPipeline instance from the Kernel
        num_chunks = await self.kernel.ingestion.ingest_path(
            tenant_id=NATIVE_TENANT_ID,
            user_id=x_user_id,
            path=file_path
        )

        # Emit telemetry
        await self._emit_telemetry("ingest", {
            "file_path": file_path,
            "session_id": session_id,
            "user_id": x_user_id,
            "chunks": num_chunks
        })

        logger.info(f"ICE Ingest: Successfully indexed {num_chunks} fragments into the indexless horizon.")
        return num_chunks

    @property
    def chat(self):
        return ChatInterface(self)

class ChatInterface:
    def __init__(self, client: IndexlessContextClient):
        self.completions = CompletionsInterface(client)

class CompletionsInterface:
    def __init__(self, client: IndexlessContextClient):
        self.client = client

    async def create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        x_session_id: str,
        x_user_id: str = "default-user",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """
        [DX] OpenAI-compliant completion method with Indexless Context.
        """
        start_time = time.time()
        gen = generate_ice_chunks(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tenant_id=NATIVE_TENANT_ID,
            session_id=x_session_id,
            user_id=x_user_id,
            client_api_key=kwargs.get("upstream_api_key"),
            client_config=self.client.config, # Pass the entire client config
            **kwargs
        )

        if stream:
            # Wrap generator to emit telemetry on completion
            async def stream_with_telemetry():
                accumulated = ""
                total_chunks = 0
                try:
                    async for chunk in gen:
                        total_chunks += 1
                        if isinstance(chunk, dict) and "choices" in chunk:
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                accumulated += delta
                        yield chunk
                finally:
                    # Emit telemetry on completion
                    await self.client._emit_telemetry("chat_completion", {
                        "model": model,
                        "session_id": x_session_id,
                        "user_id": x_user_id,
                        "duration_ms": (time.time() - start_time) * 1000,
                        "chunks": total_chunks,
                        "streaming": True,
                        "error": None
                    })
            return stream_with_telemetry()

        # Non-streaming buffer
        accumulated = None
        total_chunks = 0
        error = None
        try:
            async for chunk in gen:
                total_chunks += 1
                if isinstance(chunk, dict) and "error" in chunk:
                    error = chunk["error"]["message"]
                    raise ICEError(chunk["error"]["message"], code="ICE_ERR_UPSTREAM")
                if chunk == "[DONE]": break
                if not accumulated:
                    # First chunk: initialize accumulated with a 'message' key
                    accumulated = {
                        "choices": [{
                            "message": {
                                "role": chunk["choices"][0]["delta"].get("role", "assistant"),
                                "content": chunk["choices"][0]["delta"].get("content", "")
                            },
                            "finish_reason": None # Will be set on the last chunk
                        }],
                        "model": model # Or get from chunk if available
                    }
                else:
                    # Subsequent chunks: append content delta
                    delta_content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta_content:
                        accumulated["choices"][0]["message"]["content"] += delta_content
                    # Update finish_reason from the last chunk if present
                    if chunk.get("choices", [{}])[0].get("finish_reason"):
                        accumulated["choices"][0]["finish_reason"] = chunk["choices"][0]["finish_reason"]
        except Exception as e:
            error = str(e)
            raise
        finally:
            # Emit telemetry on completion
            await self.client._emit_telemetry("chat_completion", {
                "model": model,
                "session_id": x_session_id,
                "user_id": x_user_id,
                "duration_ms": (time.time() - start_time) * 1000,
                "chunks": total_chunks,
                "streaming": False,
                "error": error
            })
        return accumulated

async def init(license_key: str = None, **kwargs) -> IndexlessContextClient:
    global _ice_kernel, _default_client
    if not _ice_kernel:
        _ice_kernel = ICEKernel(license_key=license_key, **kwargs)
        await _ice_kernel.connect()
        await ice_server.startup()
        _default_client = IndexlessContextClient(_ice_kernel, **kwargs) # Pass kwargs here
    return _default_client

def get_client() -> IndexlessContextClient:
    if not _default_client:
        raise ICEError("ICE not initialized. Call 'await ice.init()' on startup.", code="ICE_ERR_UNINITIALIZED")
    return _default_client

class SessionManager:
    """
    [DX] Utility for extracting session and user context from web requests.
    Supports FastAPI/Starlette, Flask, and standard WSGI/ASGI request patterns.
    """
    def __init__(self, request: Any):
        # 1. User Isolation
        self.user_id = "anonymous"
        if hasattr(request, "user") and hasattr(request.user, "id"):
            self.user_id = str(request.user.id)
        elif hasattr(request, "state") and hasattr(request.state, "user_id"):
            self.user_id = str(request.state.user_id)
            
        # 2. Session Continuity
        self.session_id = None
        if hasattr(request, "headers"):
            self.session_id = request.headers.get("X-Session-Id")
        
        if not self.session_id and hasattr(request, "session"):
            self.session_id = request.session.get("ice_session_id")
            if not self.session_id:
                self.session_id = f"sess_{uuid.uuid4().hex[:12]}"
                request.session["ice_session_id"] = self.session_id
        
        if not self.session_id:
            self.session_id = f"ephem_{uuid.uuid4().hex[:12]}"
            
    def get_context(self) -> Dict[str, str]:
        """Returns headers compatible with ice_client.chat.completions.create"""
        return {
            "x_user_id": self.user_id,
            "x_session_id": self.session_id
        }
