import asyncio
from ice.core.reasoning import ReasoningExtractor
from ice.main import generate_ice_chunks
from unittest.mock import MagicMock, AsyncMock

async def debug_websocket_logic():
    print("--- Testing ReasoningExtractor ---")
    extractor = ReasoningExtractor()
    delta = "<thought>Thinking...</thought> done."
    visible_text, extracted_traces = extractor.process_chunk(delta)
    print(f"Input: {delta}")
    print(f"Visible Text: '{visible_text}'")
    print(f"Extracted Traces: {extracted_traces}")
    assert visible_text == " done."
    assert extracted_traces == [('thought', 'Thinking...')]
    print("✅ ReasoningExtractor works as expected.")

    print("
--- Testing generate_ice_chunks ---")
    async def mock_stream_iterator():
        yield b'data: {"choices": [{"delta": {"content": "Hello! "}, "index": 0}]}

'
        yield b'data: {"choices": [{"delta": {"content": "<thought>Thinking...</thought> done."}, "index": 0}]}

'
        yield b'data: [DONE]

'

    class MockResponse:
        status_code = 200
        def __init__(self):
            self.aiter_lines = mock_stream_iterator
    
    class MockClient:
        async def stream(self, *args, **kwargs):
            class MockContextManager(AsyncMock):
                async def __aenter__(self): return MockResponse()
            return MockContextManager()

    # Mock ice_server and its components
    ice_server = MagicMock()
    ice_server.http_client = MockClient()
    ice_server.degraded_mode = False
    ice_server.reasoning = AsyncMock()
    ice_server.reasoning.save_trace.return_value = None
    
    # We need to assign this mock back to the original module for the generator to use it
    import ice.main
    ice.main.ice_server = ice_server

    print("Yielded Chunks:")
    all_chunks = []
    async for chunk in generate_ice_chunks(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
        temperature=0.7,
        max_tokens=100,
        tenant_id="test",
        session_id="test",
        user_id="test",
        client_api_key="test",
    ):
        print(chunk)
        all_chunks.append(chunk)

    assert len(all_chunks) == 3, f"Expected 3 chunks, got {len(all_chunks)}"
    assert all_chunks[0]['choices'][0]['delta']['content'] == "Hello! "
    assert all_chunks[1]['choices'][0]['delta']['role'] == "thought"
    assert all_chunks[2]['choices'][0]['delta']['content'] == " done."
    print("
✅ generate_ice_chunks yielded all chunks correctly.")

if __name__ == "__main__":
    asyncio.run(debug_websocket_logic())
