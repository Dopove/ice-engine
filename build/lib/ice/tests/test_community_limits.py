import asyncio
import httpx
import pytest
import os
import docker
import asyncpg
import time

# --- Configuration for the Test ---
BASE_URL = "http://localhost:8080"
DATABASE_URL = "postgres://ice_user:ice_password@localhost:5432/ice_db"
COMMUNITY_JWT = "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzg1NzkzODgsICJleHAiOiAxODEwMTE1Mzg4LCAic3ViIjogInNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLUNPTU1VTklUWSIsICJhd3NfbGljZW5zZV9hcm4iOiAiYXJuOmF3czpsaWNlbnNlLW1hbmFnZXI6OjA1MDc1MjYxNjczMTpsaWNlbnNlOmwtMWI0YzJmOTk4YjVhNGJjMDljMjliNDYzOWJiMmFhNTMiLCAibWF4X25vZGVzIjogMSwgIm1heF_0ZW5hbnRzIjogMSwgImZlYXR1cmVzIjogW10sICJ0ZW5hbnRfaWQiOiAiODIzZGMyNGEtODg1ZS00NTg2LWE3NGItOTE0NGRjYzBmODQ5IiwgIm1hY2hpbmVfcHVibGljX2tlaXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.BecFR8Rn7FoJJY-1f4Oc5bN2UpUt5OT6kVhjNI8kj_LneVlB5a9C5SLL1lToz0BWcLupE2YMfCjC0AFzhN1hMumbQUuOiuHAJ30mRee-hqgV_R4VVfVVw1ojjDMGwpYVWuaDwPkmBPsrMbhxtw2v70mxbaiOc8QQcLbIwDpd07XSRzPAD4s_jLGpw-mYTFebKUKcaK3sXFG8tEVow98D_6smHFgc0A9Tz1EKDJzqtnsqbVJF3Kc8i3rpvAGs7IB9d-_6L0a-S0ul6FUFRqNTDfyX99BGj6jpxTzbPHvqbu80wy4LN_kOIbiKGVMdUnXoEpBGZMcfRAtwBrgpEcMeMw"

@pytest.fixture(scope="module")
def ice_environment():
    """
    Sets up and tears down the Docker Compose environment for ICE.
    Ensures a clean database state and community license.
    """
    compose_path = os.path.join(os.path.dirname(__file__), "..", "..") # Project root
    compose_file_path = os.path.join(compose_path, "docker-compose.yml")

    # Set environment variables for Docker Compose
    os.environ["ICE_TEST_MODE"] = "1"
    os.environ["ICE_ALLOW_DEFAULT_KEY"] = "0"
    os.environ["ICE_MOCK_LLM_CALL"] = "1"
    os.environ["ICE_LICENSE_JWT"] = COMMUNITY_JWT
    os.environ["ICE_SKU"] = "ICE-COMMUNITY"

    # Ensure services are down and cleaned up before starting
    os.system(f"docker compose -f {compose_file_path} down -v --remove-orphans")
    
    # Start the stack
    os.system(f"docker compose -f {compose_file_path} up -d --build --force-recreate")
    import time
    time.sleep(10)
    
    # Wait for ICE to be ready
    for _ in range(30):
        try:
            resp = httpx.get(f"{BASE_URL}/ready", timeout=1)
            if resp.status_code == 200 and resp.json().get("status") == "ready":
                print("\nICE is ready.")
                break
        except httpx.ConnectError:
            pass
        time.sleep(1)
    else:
        raise Exception("ICE did not become ready in time.")

    yield # Tests run here

    # Teardown
    os.system(f"docker compose -f {compose_file_path} down -v --remove-orphans")
    
    # Unset environment variables
    del os.environ["ICE_TEST_MODE"]
    del os.environ["ICE_ALLOW_DEFAULT_KEY"]
    del os.environ["ICE_MOCK_LLM_CALL"]
    del os.environ["ICE_LICENSE_JWT"]
    del os.environ["ICE_SKU"]


@pytest.mark.asyncio
async def test_community_max_tenants_limit(ice_environment):
    """
    Verifies that only one ICE-COMMUNITY tenant can be created.
    """
    client = httpx.AsyncClient()

    # 1. Create the first tenant (should succeed)
    print("Attempting to create first ICE-COMMUNITY tenant...")
    response_1 = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-community-1",
            "X-Session-Id": "community-session-1",
            "X-User-Id": "community-user-1"
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}
    )
    assert response_1.status_code == 200, f"Expected 200 for first tenant, got {response_1.status_code}: {response_1.text}"
    print(f"First tenant creation response: {response_1.json()}")

    # Verify tenant was created with correct SKU
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        tenant_count = await conn.fetchval("SELECT COUNT(*) FROM tenants WHERE sku = $1", "ICE-COMMUNITY")
        assert tenant_count == 1, "Expected 1 ICE-COMMUNITY tenant in DB."
    finally:
        await conn.close()

    # 2. Attempt to create a second tenant (should fail with 403)
    print("Attempting to create second ICE-COMMUNITY tenant (should fail)...")
    response_2 = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-community-2", # Different API key
            "X-Session-Id": "community-session-2",
            "X-User-Id": "community-user-2"
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Hello again"}]}
    )
    assert response_2.status_code == 403, f"Expected 403 for second tenant, got {response_2.status_code}: {response_2.text}"
    assert "only one free tier license (ice-community) is allowed per deployment" in response_2.json()["message"].lower()
    print(f"Second tenant creation response: {response_2.json()}")

@pytest.mark.asyncio
async def test_community_max_concurrent_sessions(ice_environment):
    """
    Verifies that ICE-COMMUNITY limits to 1 concurrent session.
    """
    client = httpx.AsyncClient()
    tenant_api_key = "test-concurrent-tenant"
    tenant_session_id = "concurrent-session"
    tenant_user_id = "concurrent-user"

    # Ensure a tenant exists for this API key
    await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tenant_api_key}",
            "X-Session-Id": "setup-session",
            "X-User-Id": "setup-user"
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Setup"}]}
    )
    
    # 1. Start one session (should succeed)
    print("Starting first concurrent session...")
    first_session_task = asyncio.create_task(
        client.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {tenant_api_key}",
                "X-Session-Id": tenant_session_id,
                "X-User-Id": tenant_user_id
            },
            json={"model": "llama3", "messages": [{"role": "user", "content": "Long task"}]}
        )
    )

    await asyncio.sleep(0.5) # Give time for the first session to register

    # 2. Attempt to start a second concurrent session (should fail with 429)
    print("Attempting to start second concurrent session (should fail)...")
    response_2 = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tenant_api_key}",
            "X-Session-Id": "another-concurrent-session", # Different session ID but same tenant
            "X-User-Id": tenant_user_id
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Another long task"}]}
    )

    assert response_2.status_code == 429, f"Expected 429 for second concurrent session, got {response_2.status_code}: {response_2.text}"
    assert "concurrent session limit (1) for your license tier has been reached" in response_2.json()["message"].lower()
    print(f"Second concurrent session response: {response_2.json()}")

    # Wait for the first session to complete (to clean up the semaphore)
    await first_session_task
    assert first_session_task.result().status_code == 200

@pytest.mark.asyncio
async def test_community_max_tokens_per_session(ice_environment):
    """
    Verifies that ICE-COMMUNITY enforces max_tokens_per_session.
    """
    client = httpx.AsyncClient()
    tenant_api_key = "test-token-limit-tenant"
    tenant_session_id = "token-limit-session"
    tenant_user_id = "token-limit-user"

    # Ensure a tenant exists for this API key
    await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tenant_api_key}",
            "X-Session-Id": "setup-session-tokens",
            "X-User-Id": "setup-user-tokens"
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Setup"}]}
    )

    # Simulate exceeding 10M tokens (approx 2.5MB of text)
    # The mock response is fixed, so this will only test the initial token count.
    # We need ice.episodic.save_message to actually store the token count for a session.
    # The 'Hello' message will not exceed 10M tokens, so we'll need to send a very long message.
    
    # For a mock, this is harder to test without a real LLM that can generate long responses.
    # However, the enforce logic in main.py will check episodic.get_session_token_count
    # so we can directly manipulate the DB to simulate this.
    
    # Temporarily set the session's token count in DB to just under the limit
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        tenant_row = await conn.fetchrow("SELECT tenant_id FROM tenants WHERE api_key = $1", tenant_api_key)
        tenant_id = tenant_row["tenant_id"]
        
        # Manually insert a large message to push token count over the limit
        long_content = "a" * (10_000_000 * 3) # Approximately 10M tokens (1 token ~ 4 chars)
        await conn.execute(
            """INSERT INTO episodic_ledger (id, tenant_id, user_id, session_id, role, content)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            uuid.uuid4(), tenant_id, tenant_user_id, tenant_session_id, "assistant", long_content
        )
    finally:
        await conn.close()

    print("Attempting to send a message to an over-limit session (should fail with 403)...")
    response = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tenant_api_key}",
            "X-Session-Id": tenant_session_id,
            "X-User-Id": tenant_user_id
        },
        json={"model": "llama3", "messages": [{"role": "user", "content": "Short message"}]}
    )

    assert response.status_code == 403, f"Expected 403 for over-limit session, got {response.status_code}: {response.text}"
    assert "token limit (10000000) for your license tier has been reached for this session." in response.json()["message"].lower()
    print(f"Over-limit session response: {response.json()}")
