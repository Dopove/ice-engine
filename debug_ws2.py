import os
import sys
import traceback
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

# Force default key
os.environ["ICE_ALLOW_DEFAULT_KEY"] = "1"
os.environ["ICE_LICENSE_JWT"] = "ice-default-key"

from ice.main import app, ice_server

def test_ws():
    with patch("ice.main.ice_server.db_pool") as mock_db, \
         patch("ice.main.ice_server.redis") as mock_r:
        
        mock_db.acquire = MagicMock()
        mock_cm = AsyncMock()
        mock_conn = AsyncMock()
        
        # To prevent iteration over AsyncMock, let's make fetch return a real list of dicts
        # Or a MagicMock that returns an empty list when iterated
        mock_conn.fetch.return_value = []
        mock_cm.__aenter__.return_value = mock_conn
        mock_db.acquire.return_value = mock_cm
        mock_r.eval = AsyncMock(return_value=0)
        
        with TestClient(app) as client:
            payload = {
                "model": "llama3.2:latest",
                "messages": [{"role": "user", "content": "How are you?"}],
                "stream": True,
                "tenant_id": "823dc24a-885e-4586-a74b-9144dcc0f849",
                "session_id": "98b50e2d-dc99-43ef-b387-052637738f61",
                "api_key": "ice-default-key"
            }
            async def mock_stream_iterator():
                yield b'data: {"choices": [{"delta": {"content": "Hello! "}, "index": 0}]}\n'
                yield b'data: {"choices": [{"delta": {"content": "<thought>Thinking...</thought> done."}, "index": 0}]}\n'
                yield b"data: [DONE]\n"

            with patch("httpx.AsyncClient.stream") as mock_stream:
                mock_cm = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.aiter_lines.return_value = mock_stream_iterator()
                mock_cm.__aenter__.return_value = mock_response
                mock_stream.return_value = mock_cm

                with client.websocket_connect("/v1/ws/chat") as websocket:
                    websocket.send_json(payload)
                    
                    # Receive first chunk
                    msg1 = websocket.receive_text()
                    print("MSG1:", msg1)

if __name__ == "__main__":
    test_ws()