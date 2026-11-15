# SPDX-License-Identifier: BSL-1.1

# ice/node_bridge.py
import sys
import os

# Redirect standard output to standard error to prevent logs from polluting the JSON response
# Node.js expects exactly one JSON object on stdout.
original_stdout = sys.stdout
sys.stdout = sys.stderr

import asyncio
import json

# This script acts as a high-speed IPC (Inter-Process Communication) bridge
# between the Node.js C++ layer and the native Python ICE Kernel.
# It avoids the overhead of a full HTTP server for the embedded Node.js package.

async def handle_request(ice_client, completion_params, original_stdout):
    """Handles the core logic of streaming vs. non-streaming response."""
    if completion_params.get("stream"):
        # Streaming response
        async for chunk in await ice_client.chat.completions.create(**completion_params):
            # SSE format: data: {json_chunk}\n\n
            original_stdout.write(f"data: {json.dumps(chunk)}\n\n")
            original_stdout.flush()
        original_stdout.write("data: [DONE]\n\n")
        original_stdout.flush()
    else:
        # Non-streaming response
        response = await ice_client.chat.completions.create(**completion_params)
        original_stdout.write(json.dumps(response))

async def main():
    # 1. Read the full request payload from stdin
    request_str = sys.stdin.read()
    if not request_str:
        return

    request_data = json.loads(request_str)

    # 2. Extract parameters for the ICE SDK
    sdk_params = request_data.get("sdk_params", {})
    completion_params = request_data.get("completion_params", {})

    # The Node.js wrapper MUST pass all necessary env vars
    # for DB/Redis connections and license keys.

    try:
        from ice.sdk import init, get_client

        # 3. Initialize the ICE Kernel
        await init(**sdk_params)
        ice_client = get_client()

        # 4. Execute the request handler
        await handle_request(ice_client, completion_params, original_stdout)

    except BaseException as e:
        # If anything fails, write a JSON error to stderr
        error_response = {
            "error": {
                "type": type(e).__name__,
                "message": str(e)
            }
        }
        sys.stderr.write(json.dumps(error_response))
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
