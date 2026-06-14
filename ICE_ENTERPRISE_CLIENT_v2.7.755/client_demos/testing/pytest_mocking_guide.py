import pytest
import asyncio
from unittest.mock import patch

# 1. Import your application code
# Assume you have a feature like this in your app:
async def my_agentic_function(prompt: str, user_id: str, session_id: str, ice_client):
    # This function usually makes a live call to the ICE Engine
    response = await ice_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        x_user_id=user_id,
        x_session_id=session_id
    )
    return response.choices[0].message.content

# 2. Import the ICE Mock Testing Utility
# ICE ships with a lightweight mock client specifically designed for fast CI/CD pipelines
from ice.testing import mock_client

@pytest.mark.asyncio
async def test_my_agent_in_ci():
    """
    Demonstrates how Enterprise Teams can run thousands of unit tests 
    in their CI/CD pipelines (GitHub Actions, GitLab) WITHOUT spinning up 
    a PostgreSQL database or paying for upstream LLM API tokens.
    """
    print("\n[CI Test]: Initializing Offline ICE Mock Client...")
    
    # Instantiate the mock
    fake_ice = mock_client()
    
    # 3. Prime the Mock Responses
    # Pre-program the exact response you want ICE to return for specific prompts
    test_prompt = "What is the status of the server?"
    expected_result = "The server is running perfectly with 0 downtime."
    
    fake_ice.add_response(
        test_prompt, 
        {"choices": [{"message": {"content": expected_result}}]}
    )
    
    # 4. Execute your application logic using the Mock Client
    print(f"[CI Test]: Injecting mock and executing agentic function...")
    result = await my_agentic_function(
        prompt=test_prompt,
        user_id="test-user-01",
        session_id="test-session-99",
        ice_client=fake_ice
    )
    
    # 5. Assert the result
    assert result == expected_result
    print(f"[CI Test]: Success! Agent returned: '{result}'")
    print("[CI Test]: Zero tokens consumed. Zero database connections required.")

if __name__ == "__main__":
    asyncio.run(test_my_agent_in_ci())
