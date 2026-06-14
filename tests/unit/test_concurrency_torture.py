import asyncio
import httpx
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)

# Dummy Upstream LLM Server
async def mock_chat_completions(request):
    return web.json_response({
        "id": "mock-123",
        "object": "chat.completion",
        "created": 123456,
        "model": "mock-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Mock dummy response."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    })

async def run_mock_server():
    app = web.Application()
    app.router.add_post('/v1/chat/completions', mock_chat_completions)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8888)
    await site.start()
    logging.info("Started mock upstream server on 8888")
    return runner

# Torture Test Client
async def fire_request(client, ICE_URL, headers, payload, worker_id):
    try:
        response = await client.post(ICE_URL, headers=headers, json=payload, timeout=30.0)
        return response.status_code
    except Exception as e:
        return str(e)

import pytest

@pytest.mark.skip(reason="Networking dependent test")
async def test_concurrency():
    ICE_URL = "http://localhost:8081/v1/chat/completions"
    import uuid
    HEADERS = {
        "Authorization": f"Bearer {uuid.uuid4()}",
        "X-Session-Id": "concurrency-session"
    }
    PAYLOAD = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "Hello."}]
    }

    # We fire 110 requests simultaneously. The window is 60s, limit is 100.
    # Expect 100 successes (200), 10 rate-limits (429).
    concurrency = 110
    logging.info(f"Firing {concurrency} simultaneous requests...")
    
    async with httpx.AsyncClient() as client:
        tasks = [fire_request(client, ICE_URL, HEADERS, PAYLOAD, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)

    status_counts = {}
    for r in results:
        status_counts[r] = status_counts.get(r, 0) + 1
        
    logging.info(f"Concurrency Result Statuses: {status_counts}")
    
    assert status_counts.get(200, 0) == 100, f"Expected exactly 100 OKs, got {status_counts.get(200, 0)}"
    assert status_counts.get(429, 0) == 10, f"Expected exactly 10 Rate Limits, got {status_counts.get(429, 0)}"
    logging.info("[SUCCESS] Sliding-Window Rate Limiter gracefully handled the concurrency torture!")

async def main():
    runner = await run_mock_server()
    await test_concurrency()
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
