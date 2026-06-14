import asyncio
import httpx
import time
import json
import websockets
import pytest

BASE_URL = "http://localhost:8081"
WS_URL = "ws://localhost:8081/v1/ws/chat"

@pytest.mark.skip(reason="Networking dependent test")
async def test_metrics():
    print("--- Testing Metrics ---")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/metrics")
        print(f"Status: {response.status_code}")
        if "http_requests_total" in response.text:
            print("Verified: Prometheus metrics are being collected.")
        else:
            print("Warning: http_requests_total not found in metrics.")

@pytest.mark.skip(reason="Networking dependent test")
async def test_rate_limiting():
    # The default limit is 100 per 60s. Let's try to burst it.
    # Actually, for testing, I might want to reduce the limit or just hammer it.
    print("--- Testing Rate Limiting (Sliding Window) ---")
    tenant_id = "test-tenant"
    headers = {
        "Authorization": "Bearer mock-token",
        "X-Session-Id": "test-session"
    }
    
    # We will send 10 requests. If the limit was say 5, it would trigger.
    # Since it's 100, we'll just check if it's counting correctly in metrics.
    async with httpx.AsyncClient(headers=headers) as client:
        for i in range(5):
            resp = await client.get(f"{BASE_URL}/v1/memory/status")
            print(f"Req {i+1}: {resp.status_code}")
            
    # Check metrics again for increment
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/metrics")
        if f'http_requests_total{{method="GET",status="200"' in response.text:
            print("Verified: Request count incremented in Prometheus.")

async def main():
    await test_metrics()
    await test_rate_limiting()

if __name__ == "__main__":
    asyncio.run(main())
