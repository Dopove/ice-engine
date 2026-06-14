import uvicorn
from fastapi import FastAPI
from api.routes.chat_routes import router as chat_router
from contextlib import asynccontextmanager

# ==============================================================================
# MAIN APPLICATION ENTRYPOINT
# ==============================================================================

@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    from api.core.ice_config import startup_ice, get_ice
    await startup_ice()
    yield
    # Shutdown logic if any
    ice_client = get_ice()
    if ice_client:
        print("[ICE Shutdown]: Disconnecting Infinite Context Engine...")
        await ice_client.shutdown() # Ensure proper connection closing
        print("[ICE Shutdown]: Engine disconnected.")


app = FastAPI(
    title="Enterprise ICE Engine Example",
    description="A demonstration of integrating the ICE Kernel into a production FastAPI application.",
    version="2.7.755",
    lifespan=lifespan_manager
)

# Register the routes that utilize the ICE Singleton
app.include_router(chat_router)

@app.get("/health")
async def health_check():
    return {"status": "online", "engine": "ICE v2.7.755"}

if __name__ == "__main__":
    print("🚀 Starting Enterprise ICE Engine Example...")
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
