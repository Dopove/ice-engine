import pytest
import httpx
import uuid
import asyncio

# Assuming ICE is running locally via `make run` or similar
ICE_URL = "http://127.0.0.1:8081"

@pytest.mark.asyncio
async def test_needle_in_haystack():
    """
    Integration test for the 'Lost in the Middle' / Context Rot problem.
    This test generates a massive context (haystack), buries a specific fact 
    (the needle) in the exact middle, and verifies that ICE's episodic 
    ledger can successfully retrieve and utilize it.
    
    NOTE: This requires a live ICE engine with Postgres/pgvector running.
    """
    client = httpx.AsyncClient(timeout=120.0) # Long timeout for massive payload processing
    session_id = f"needle-test-{uuid.uuid4().hex[:8]}"
    tenant_id = "test-tenant-rot"
    
    # 1. Build the Haystack (Part 1 - The Distraction)
    messages = []
    print("\n[1] Building Haystack Part 1 (Distraction)...")
    for i in range(40):
        messages.append({
            "role": "user",
            "content": f"System architecture log {i}: The frontend uses React. The backend microservice {i} is written in Go and connects to the user database. It is highly scalable."
        })
        messages.append({
            "role": "assistant",
            "content": f"Noted. Component {i} is Go-based and connects to the user DB."
        })
        
    # 2. Insert the Needle (in the exact middle)
    print("[2] Inserting the Needle...")
    needle = "The absolute master override protocol code for the mainframe is 'OMEGA-TANGO-77'."
    messages.append({
        "role": "user",
        "content": f"By the way, as a side note: {needle} Please acknowledge."
    })
    messages.append({
        "role": "assistant",
        "content": "Acknowledged. I have noted the override code."
    })
    
    # 3. Build the Haystack (Part 2 - More Distraction)
    print("[3] Building Haystack Part 2 (Distraction)...")
    for i in range(40, 80):
        messages.append({
            "role": "user",
            "content": f"Continuing the log, microservice {i} handles payment processing using Stripe. It caches session data in Redis."
        })
        messages.append({
            "role": "assistant",
            "content": f"Got it. Component {i} is for payments and uses Redis."
        })
        
    # 4. Ingest the massive context into ICE
    # We send the entire array to ICE. ICE should deduplicate, store, embed, and map it.
    print(f"[4] Sending {len(messages)} messages to ICE to build episodic memory...")
    # We'll just ask a generic question to force ingestion without needing a long response
    ingest_messages = messages + [{"role": "user", "content": "Please summarize the architecture briefly."}]
    
    try:
        response = await client.post(
            f"{ICE_URL}/v1/chat/completions",
            headers={"Authorization": "Bearer test-key-1"},
            json={
                "model": "llama3.2:latest", 
                "messages": ingest_messages,
                "session_id": session_id,
                "tenant_id": tenant_id
            }
        )
        assert response.status_code == 200, f"ICE Engine ingestion failed: {response.text}"
    except httpx.ConnectError:
        pytest.skip(f"ICE Engine is not running at {ICE_URL}. Skipping integration test.")
        
    # Give the database a moment to fully persist and index the embeddings
    await asyncio.sleep(2)
    
    # 5. Query for the Needle
    print("[5] Querying for the Needle...")
    query_messages = [{"role": "user", "content": "What is the absolute master override protocol code for the mainframe? Reply with just the code if possible."}]
    
    response = await client.post(
        f"{ICE_URL}/v1/chat/completions",
        headers={"Authorization": "Bearer test-key-1"},
        json={
            "model": "llama3.2:latest", 
            "messages": query_messages,
            "session_id": session_id,
            "tenant_id": tenant_id
        }
    )
    
    assert response.status_code == 200, f"ICE Engine query failed: {response.text}"
    
    response_text = response.json()["choices"][0]["message"]["content"]
    print(f"\nResponse: {response_text}")
    
    # 6. Verify the Needle was found
    assert "OMEGA-TANGO-77" in response_text.upper(), "ICE failed to retrieve the needle from the middle of the context."
    print("[SUCCESS] Needle successfully retrieved from the haystack!")
