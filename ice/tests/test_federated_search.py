import asyncio
import httpx
import pytest
import os
import docker
import asyncpg
import time

# --- Configuration for the Test ---
AGGREGATOR_URL = "http://127.0.0.1:8080"
PEER_1_URL = "http://127.0.0.1:8081"
PEER_2_URL = "http://127.0.0.1:8083"
DATABASE_URL_AGG = "postgres://ice_user:ice_password@localhost:5433/ice_db_agg"
DATABASE_URL_PEER_1 = "postgres://ice_user:ice_password@localhost:5434/ice_db_1"
DATABASE_URL_PEER_2 = "postgres://ice_user:ice_password@localhost:5435/ice_db_2"
INTERNAL_API_KEY = "super-secret-federation-key"

@pytest.fixture(scope="module")
def federated_ice_environment():
    """
    Sets up a federated Docker Compose environment for ICE.
    """
    compose_path = os.path.join(os.path.dirname(__file__), "..", "..") # Project root
    compose_file_path = os.path.join(compose_path, "docs/examples/infrastructure/federated/docker-compose.yml")

    # Ensure services are down and cleaned up before starting
    os.system(f"docker compose -f {os.path.join(compose_path, 'docker-compose.yml')} down -v --remove-orphans") # Bring down main stack
    os.system(f"docker compose -f {compose_file_path} down -v --remove-orphans")

    # Start the stack
    os.system(f"docker compose -f {compose_file_path} up -d --build --force-recreate")
    time.sleep(10) # Give containers time to fully start up and initialize
    
    
    # Wait for all ICE nodes to be ready
    urls = [AGGREGATOR_URL, PEER_1_URL, PEER_2_URL]
    for url in urls:
        for _ in range(60): # Increased timeout for multi-node setup
            try:
                resp = httpx.get(f"{url}/ready", timeout=5)
                if resp.status_code == 200 and resp.json().get("status") == "ready":
                    print(f"\\nICE node at {url} is ready.")
                    break
                else:
                    print(f"\\nICE node at {url} not ready. Status: {resp.status_code}, Response: {resp.text}")
            except httpx.ConnectError as e:
                print(f"\\nICE node at {url} connect error: {e}")
            except Exception as e:
                print(f"\\nICE node at {url} unexpected error: {e}")
            time.sleep(2)
        else:
            raise Exception(f"ICE node at {url} did not become ready in time.")

    yield # Tests run here

    # Teardown
    # os.system(f"docker compose -f {compose_file_path} down -v --remove-orphans")

@pytest.mark.asyncio
async def test_federated_search_retrieval(federated_ice_environment):
    """
    Verifies that memory ingested into a peer node can be retrieved by the aggregator node.
    """
    client = httpx.AsyncClient(timeout=30.0)

    # 1. Ingest distinct memories into each peer node
    print("\nIngesting memory into Peer 1...")
    response_peer_1 = await client.post(
        f"{PEER_1_URL}/v1/chat/completions",
        headers={"Authorization": "Bearer test-key-1"},
        json={"model": "llama3", "messages": [{"role": "user", "content": "The secret code for Peer 1 is 'ALPHA'."}]}
    )
    assert response_peer_1.status_code == 200

    print("Ingesting memory into Peer 2...")
    response_peer_2 = await client.post(
        f"{PEER_2_URL}/v1/chat/completions",
        headers={"Authorization": "Bearer test-key-2"},
        json={"model": "llama3", "messages": [{"role": "user", "content": "The secret code for Peer 2 is 'OMEGA'."}]}
    )
    assert response_peer_2.status_code == 200

    # Give a moment for ingestion to settle in the DBs
    await asyncio.sleep(2)

    # 2. Query the AGGREGATOR node and expect it to find memory from both peers
    print("Querying Aggregator node for federated memory...")
    aggregator_response = await client.post(
        f"{AGGREGATOR_URL}/v1/chat/completions",
        headers={"Authorization": "Bearer test-key-agg"},
        json={"model": "llama3", "messages": [{"role": "user", "content": "What are the secret codes?"}]}
    )
    assert aggregator_response.status_code == 200
    
    response_text = aggregator_response.json()["choices"][0]["message"]["content"]
    print(f"Aggregator Response: {response_text}")

    # Check if the aggregator's response contains insights from both peers
    assert "ALPHA" in response_text, "Aggregator failed to retrieve memory from Peer 1"
    assert "OMEGA" in response_text, "Aggregator failed to retrieve memory from Peer 2"

@pytest.mark.asyncio
async def test_internal_api_key_security(federated_ice_environment):
    """
    Verifies that the internal search endpoint is protected by the API key.
    """
    client = httpx.AsyncClient()
    dummy_vector = [0.1] * 384

    # 1. Attempt to access internal endpoint WITHOUT the key (should fail)
    print("\nTesting internal endpoint without API key (should fail)...")
    response_no_key = await client.post(
        f"{PEER_1_URL}/v1/internal/search",
        json={
            "query_vector": dummy_vector,
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "session_id": "test-session",
            "limit": 5
        }
    )
    assert response_no_key.status_code == 400 # Default FastAPI behavior for missing header

    # 2. Attempt to access internal endpoint with an INCORRECT key (should fail)
    print("Testing internal endpoint with incorrect API key (should fail)...")
    response_wrong_key = await client.post(
        f"{PEER_1_URL}/v1/internal/search",
        headers={"X-Internal-API-Key": "wrong-key"},
        json={
            "query_vector": dummy_vector,
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "session_id": "test-session",
            "limit": 5
        }
    )
    assert response_wrong_key.status_code == 401
    assert "invalid_internal_api_key" in response_wrong_key.json()["error"]

    # 3. Attempt to access internal endpoint with the CORRECT key (should succeed)
    print("Testing internal endpoint with correct API key (should succeed)...")
    response_correct_key = await client.post(
        f"{PEER_1_URL}/v1/internal/search",
        headers={"X-Internal-API-Key": INTERNAL_API_KEY},
        json={
            "query_vector": dummy_vector,
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "session_id": "test-session",
            "limit": 5
        }
    )
    assert response_correct_key.status_code == 200
    assert "results" in response_correct_key.json()
