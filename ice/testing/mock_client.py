# SPDX-License-Identifier: BSL-1.1

from unittest.mock import AsyncMock

class MockClient:
    """
    A drop-in replacement for IndexlessContextClient for testing environments.
    Simulates network calls and responses without infrastructure.
    """
    def __init__(self, *args, **kwargs):
        self.chat = AsyncMock()
        self.chat.completions = AsyncMock()
        self.chat.completions.create = AsyncMock(side_effect=self._mock_completion)
        self.ingest = AsyncMock(return_value={"status": "success", "chunks": 5})

    async def _mock_completion(self, *args, **kwargs):
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        class MockChoice:
            def __init__(self, message):
                self.message = message
        
        class MockResponse:
            def __init__(self, choices):
                self.choices = choices
        
        return MockResponse([MockChoice(MockMessage("Mocked ICE response"))])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
