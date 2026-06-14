from fastapi import FastAPI, HTTPException
import uvicorn
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

from app.core.ice_config import initialize_ice_kernel, get_ice_client
from app.api.endpoints import ice_endpoints

@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    """
    Initializes and cleans up ICE Kernel resources during application lifecycle.
    """
    await initialize_ice_kernel()
    yield
    ice_client = get_ice_client()
    if ice_client:
        print("[ICE Shutdown]: Disconnecting Infinite Context Engine...")
        await ice_client.shutdown() # Ensure proper connection closing
        print("[ICE Shutdown]: Engine disconnected.")


app = FastAPI(
    title="DOPOVE ICE Enterprise API Server",
    description="Full-fledged example of a FastAPI server integrated with the Infinite Context Engine.",
    version="2.7.755",
    lifespan=lifespan_manager
)

# Include ICE API endpoints
app.include_router(ice_endpoints.router, prefix="/v1")

@app.get("/health", summary="Health Check")
async def health_check():
    """
    Checks the health status of the API server and the underlying ICE Kernel.
    """
    try:
        ice_client = get_ice_client()
        ice_status = await ice_client.health() # ICE SDK provides a health check
        return {
            "status": "online",
            "api_server": "healthy",
            "ice_kernel": ice_status
        }
    except RuntimeError as e: # ICE Kernel not initialized
        raise HTTPException(status_code=503, detail=f"API Server OK, but ICE Kernel not ready: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ICE Kernel health check failed: {e}")


if __name__ == "__main__":
    print(f"🚀 Starting DOPOVE ICE Enterprise API Server (v{app.version})")
    # To run this directly:
    # uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, workers=int(os.getenv("ICE_WORKERS", "1")))
