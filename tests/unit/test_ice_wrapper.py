import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ice.wrapper import ICEWrapper
from ice.proxy.policy import MemoryPolicy
from ice.store.base import MemoryStore

class MockLLMClient:
    def __init__(self):
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock()

@pytest.mark.asyncio
async def test_icewrapper_passthrough():
    mock_llm = MockLLMClient()
    wrapper = ICEWrapper(mock_llm)

    # Test that non-intercepted calls pass through
    wrapper.chat.completions.list()
    mock_llm.chat.completions.list.assert_called_once()

@pytest.mark.asyncio
async def test_icewrapper_intercepts_create():
    mock_llm = MockLLMClient()
    wrapper = ICEWrapper(mock_llm)

    messages = [{"role": "user", "content": "Hello"}]
    
    # Mock memory interactions
    wrapper.memory.retrieve = AsyncMock(return_value=[])
    wrapper.memory.save = AsyncMock()

    await wrapper.chat.completions.create(messages=messages)
    
    wrapper.memory.retrieve.assert_called_once_with("Hello")
    mock_llm.chat.completions.create.assert_called_once()
    wrapper.memory.save.assert_called_once()

@pytest.mark.asyncio
async def test_icewrapper_injects_memory():
    mock_llm = MockLLMClient()
    wrapper = ICEWrapper(mock_llm)

    messages = [{"role": "user", "content": "What is ICE?"}]
    retrieved_memory = ["ICE is an open-source memory engine."]
    
    wrapper.memory.retrieve = AsyncMock(return_value=retrieved_memory)
    wrapper.memory.save = AsyncMock()

    await wrapper.chat.completions.create(messages=messages)
    
    # Verify memory was injected into the last user message
    args, kwargs = mock_llm.chat.completions.create.call_args
    modified_messages = kwargs['messages']
    
    assert "ICE is an open-source memory engine." in modified_messages[0]['content']
    assert "[Recalled Memory]: ICE is an open-source memory engine." in modified_messages[0]['content']

@pytest.mark.asyncio
async def test_icewrapper_handles_streaming_response():
    mock_llm = MockLLMClient()
    wrapper = ICEWrapper(mock_llm)

    # Mock a streaming response from the original client
    async def mock_streaming_response():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))])
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="!"))])
    
    mock_llm.chat.completions.create.return_value = mock_streaming_response()
    
    wrapper.memory.retrieve = AsyncMock(return_value=[])
    wrapper.memory.save = AsyncMock()

    stream_generator = await wrapper.chat.completions.create(messages=[], stream=True)
    
    full_response_content = ""
    async for chunk in stream_generator:
        if chunk.choices:
            full_response_content += chunk.choices[0].delta.content

    assert full_response_content == "Hello world!"
    wrapper.memory.save.assert_called_once_with("assistant", "Hello world!")

@pytest.mark.asyncio
async def test_icewrapper_handles_non_streaming_response():
    mock_llm = MockLLMClient()
    wrapper = ICEWrapper(mock_llm)

    # Mock a non-streaming response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock(content="Non-streaming response.")
    mock_llm.chat.completions.create.return_value = mock_response
    
    wrapper.memory.retrieve = AsyncMock(return_value=[])
    wrapper.memory.save = AsyncMock()

    response = await wrapper.chat.completions.create(messages=[], stream=False)
    
    assert response.choices[0].message.content == "Non-streaming response."
    wrapper.memory.save.assert_called_once_with("assistant", "Non-streaming response.")
