# ice/testing.py
from unittest.mock import MagicMock

class MockCompletions:
    def __init__(self):
        self._responses = {}
        self._default_response = {
            "choices": [{"message": {"content": "This is a mock response."}}]
        }

    def add_response(self, prompt_text, response_data):
        """Queue a specific response for a prompt."""
        self._responses[prompt_text] = response_data

    async def create(self, messages, **kwargs):
        """Return a queued response or the default."""
        last_user_message = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if last_user_message:
            prompt = last_user_message["content"]
            if prompt in self._responses:
                return self._responses.pop(prompt)
        return self._default_response

class MockChat:
    def __init__(self):
        self.completions = MockCompletions()

class MockICEClient:
    def __init__(self):
        self.chat = MockChat()
        self.ingest = MagicMock()

    def add_response(self, prompt, response):
        """Helper to directly add a response to the mock completions."""
        self.chat.completions.add_response(prompt, response)

def mock_client():
    """Returns a mock ICE client for testing."""
    return MockICEClient()
