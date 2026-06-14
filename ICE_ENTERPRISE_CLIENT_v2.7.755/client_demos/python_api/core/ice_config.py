
import os
from ice.sdk import init, get_client

print("[System]: Booting Global ICE Kernel Configuration...")
os.environ.setdefault("ICE_MEMORY_CAP_GB", "32.0")

async def startup_ice():
    await init(max_input_tokens=128000)

def get_ice():
    return get_client()
