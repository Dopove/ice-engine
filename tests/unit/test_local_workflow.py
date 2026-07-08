import pytest
import os
import duckdb
from unittest.mock import AsyncMock, MagicMock
from ice.wrapper import ICEWrapper

class DummyClient:
    def __init__(self):
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock()

@pytest.mark.asyncio
async def test_duckdb_end_to_end_local_workflow(tmp_path):
    """
    Tests the full ICEWrapper workflow using the local DuckDB MemoryStore.
    This proves the 'Zero-Conf' onboarding works perfectly.
    """
    # Use a temporary file for the DuckDB database to keep tests isolated
    db_path = str(tmp_path / "test_memory.db")
    
    # Setup dummy client
    dummy = DummyClient()
    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock(content="I will remember that your favorite color is blue.")
    dummy.chat.completions.create.return_value = mock_response

    # Initialize wrapper with the local db path (Zero-Conf mode)
    wrapper = ICEWrapper(client=dummy, connection_string=db_path)

    # 1. First turn: No memory yet
    messages = [{"role": "user", "content": "My favorite color is blue."}]
    await wrapper.chat.completions.create(messages=messages, stream=False)
    
    # Verify the LLM was called
    assert dummy.chat.completions.create.call_count == 1
    
    # 2. Verify memory was saved to DuckDB locally
    con = duckdb.connect(db_path, read_only=True)
    res = con.execute("SELECT content FROM episodic_memory").fetchall()
    con.close()
    
    # We expect 1 record saved (the assistant's response)
    assert len(res) == 1
    assert res[0][0] == "I will remember that your favorite color is blue."
    
    # 3. Second turn: The wrapper should retrieve the memory automatically
    messages2 = [{"role": "user", "content": "What is my favorite color?"}]
    await wrapper.chat.completions.create(messages=messages2, stream=False)
    
    # Check what was passed to the LLM the second time
    args, kwargs = dummy.chat.completions.create.call_args
    injected_messages = kwargs['messages']
    
    # The first message in the payload should now have the memory injected
    assert "[Recalled Memory]:" in injected_messages[0]['content']
    assert "I will remember that your favorite color is blue." in injected_messages[0]['content']
