import asyncio
import os
import sys
import orjson
import logging
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, List, Any

# Configure basic logging for the client script
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock dependencies needed by generate_ice_chunks
class MockAsyncpgPool:
    async def acquire(self):
        return MockConnection()

class MockConnection:
    async def execute(self, *args, **kwargs):
        pass # Simulate DB operation

class MockRedis:
    async def get(self, key):
        return None # No cached embeddings
    async def set(self, key, value, ex):
        pass # Simulate Redis operation

class MockEmbeddingModel:
    async def embed_async(self, text):
        # Return a dummy vector
        return [0.1] * 384

class MockContextPager:
    def __init__(self):
        self.embedder = MockEmbeddingModel()
        self.max_tokens = 8192
        self.max_input_tokens = 8192
        self.default_output_tokens = 1024
        self.enable_smart_sizing = False
        self.stitch_tail = 2000

    def estimate_tokens(self, content) -> int:
        if isinstance(content, str):
            return len(content) // 4 + 1
        if isinstance(content, list): # Basic multimodal support for content estimation
            total = 0
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    total += len(item.get("text", "")) // 4 + 1
            return total
        return 0

    def get_dynamic_budget(self, model_id: str) -> int:
        return 32768 # Fixed for local models

    def get_smart_output_budget(self, messages: list[dict]) -> int:
        return 2048 # Fixed output budget for simplicity

    def assemble_prompt(
        self,
        current_request: list[dict],
        historical_messages: list[dict],
        retrieved_insights: list[str],
        reasoning_traces: Optional[list[str]] = None,
        model_id: str = "llama2:latest",
    ) -> tuple[list[dict], int, int]:
        # Simplified assemble_prompt for testing purposes
        all_messages = historical_messages + current_request
        token_count = sum(self.estimate_tokens(m["content"]) for m in all_messages)
        output_budget = self.get_smart_output_budget(all_messages)
        logger.debug(f"Mock Pager: Assembled prompt with {token_count} tokens, output budget {output_budget}")
        return all_messages, token_count, output_budget


# Create a mock ice_server
mock_ice_server = MagicMock()
mock_ice_server.db_pool = MockAsyncpgPool()
mock_ice_server.redis = MockRedis()
mock_ice_server.episodic = AsyncMock()
mock_ice_server.reasoning = AsyncMock()
mock_ice_server.rag = AsyncMock()
mock_ice_server.http_client = AsyncMock()
mock_ice_server.degraded_mode = False

# Mock the httpx.AsyncClient.stream method
# This mock needs to return an async context manager that yields data
class MockResponse:
    def __init__(self, content_chunks):
        self.status_code = 200
        self._content_chunks = content_chunks
        self.headers = {"content-type": "text/event-stream"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def aiter_lines(self):
        for chunk in self._content_chunks:
            yield f"data: {orjson.dumps(chunk).decode()}"
        yield "data: [DONE]"

# This mock simulates Ollama's streaming response for each turn
# It yields content for "Task X" and then a finish_reason "stop"
# We simulate the content generation and then a stop.
async def mock_ollama_stream_for_turn(messages_in_turn):
    # Determine which task is being asked for based on the prompt
    user_message = messages_in_turn[-1].get("content", "").lower()
    if "task 1" in user_message:
        content = "Task 1: The Roman Empire was a powerful and influential civilization that originated in the city of Rome in 753 BC. It grew from a small city-state into a vast empire that dominated much of Europe, North Africa, and the Middle East for over a thousand years. Its history is typically divided into two main periods: the Roman Republic (509 BC – 27 BC) and the Roman Empire (27 BC – 476 AD in the West, 1453 AD in the East). The Republic was characterized by a complex system of elected officials, a powerful Senate, and a citizen assembly. Its expansion was driven by military conquest, strategic alliances, and the establishment of Roman colonies. Key figures like Julius Caesar played pivotal roles in its transition from Republic to Empire. The Empire, established under Augustus, brought a period of relative peace and prosperity known as the Pax Romana. This era saw significant advancements in engineering, architecture, law, and governance. The empire reached its greatest territorial extent under Emperor Trajan in the early 2nd century AD. However, internal strife, economic problems, political instability, and pressure from external barbarian tribes eventually led to its decline and the eventual collapse of the Western Roman Empire in 476 AD. The Eastern Roman Empire, also known as the Byzantine Empire, continued to thrive for another thousand years, preserving Roman law and culture. The legacy of the Roman Empire is immense, influencing Western civilization in countless ways, from its legal systems and political structures to its languages, literature, and architectural styles. Its impact continues to be studied and admired today, shaping our understanding of governance, military strategy, and societal development."
    elif "task 2" in user_message:
        content = "Task 2: The Mongol Empire, founded by Genghis Khan in the early 13th century, was the largest contiguous land empire in history. Originating in the steppes of Central Asia, the Mongol armies, renowned for their equestrian skills and military tactics, rapidly expanded across Asia, Eastern Europe, and the Middle East. Under Genghis Khan and his successors, the empire conquered vast territories, including China (Yuan Dynasty), Persia, and much of Russia. The empire's rapid expansion was characterized by brutal efficiency in warfare but also facilitated unprecedented cultural exchange and trade along the Silk Road, a period sometimes referred to as the Pax Mongolica. The Mongols established sophisticated communication systems (Yam) and fostered tolerance for various religions and cultures within their domain. Despite its immense size and power, the empire eventually fragmented into several successor states, such as the Golden Horde, the Chagatai Khanate, the Ilkhanate, and the Yuan Dynasty in China. These successor states continued to exert significant influence for centuries. The legacy of the Mongol Empire is complex, marked by both widespread destruction and significant contributions to global interconnectedness, military innovation, and the exchange of knowledge between East and West. Its impact on the demographic and political landscape of Eurasia was profound and long-lasting."
    elif "task 3" in user_message:
        content = "Task 3: The British Empire was the largest empire in history, spanning several centuries and encompassing a quarter of the world's land area and a fifth of its population at its peak in the early 20th century. Its origins can be traced to the maritime expansion of England in the late 16th century, driven by trade, colonization, and naval power. Key periods include the establishment of colonies in North America and the Caribbean, the expansion into India through the East India Company, and the colonization of Australia and parts of Africa. The Industrial Revolution fueled Britain's imperial ambitions, providing technological superiority and economic power. The empire was characterized by diverse forms of governance, from direct rule to protectorates and dominions. British influence spread its language, legal systems, parliamentary government, and technological advancements across the globe. However, it was also marked by exploitation, slavery, famine, and violent suppression of resistance movements. Decolonization accelerated after World War II, driven by rising nationalist movements and Britain's weakened economic state. While the empire formally dissolved, its legacy continues to shape global politics, economics, and culture, particularly through the Commonwealth of Nations and the enduring impact on the former colonies."
    elif "task 4" in user_message:
        content = "Task 4: The Ottoman Empire, founded by Osman I in the late 13th century in Anatolia, rose to become one of the most powerful and long-lasting empires in world history, spanning over 600 years. At its zenith in the 16th and 17th centuries, it controlled vast territories in Southeast Europe, North Africa, and the Middle East. The empire was a multi-ethnic, multi-religious state that served as a bridge between the Eastern and Western worlds. Its military might, particularly the Janissaries, was formidable, and its naval power dominated the Mediterranean. Under sultans like Suleiman the Magnificent, the empire flourished, making significant contributions in art, architecture, science, and law. It absorbed elements from various cultures it encountered, creating a unique Ottoman identity. However, by the 18th century, the empire began a long period of decline due to internal corruption, military defeats against European powers, and a failure to modernize at the same pace as its rivals. Nationalist uprisings in the Balkans further eroded its territories. The 'Sick Man of Europe,' as it was known, finally collapsed after World War I, leading to the establishment of the Republic of Turkey and the modern states of the Middle East. Its legacy is deeply intertwined with the history of the regions it once governed."
    elif "task 5" in user_message:
        content = "Task 5: The required launch code is: OBSIDIAN-ECLIPSE-9934"
    else:
        content = "I am a helpful assistant. I don't know that yet."
    
    # Simulate streaming
    for char in content:
        yield {"choices": [{"delta": {"content": char}, "index": 0}]}
        await asyncio.sleep(0.001) # Small delay to simulate stream

    yield {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]}


mock_ice_server.http_client.stream.return_value = AsyncMock()
mock_ice_server.http_client.stream.return_value.__aenter__.return_value = MockResponse([])

# Import the actual function to test
from ice.main import generate_ice_chunks

async def main():
    logger.info("Starting direct stitching debug test...")

    # Set environment variables for the mock server to pick up
    os.environ["DATABASE_URL"] = "postgres://ice_user:ice_password@localhost:5433/ice_db"
    os.environ["REDIS_URL"] = "redis://localhost:6380/0"
    os.environ["UPSTREAM_API_URL"] = "http://localhost:11434/v1/chat/completions"
    os.environ["OPENAI_API_KEY"] = "sk-mock-key"
    os.environ["ICE_MODEL_CONTEXT_WINDOW"] = "8192"
    os.environ["ICE_POST_COMPRESSION_LIMIT"] = "8192"
    os.environ["ICE_DEFAULT_OUTPUT_TOKENS"] = "1024"
    os.environ["ICE_DYNAMIC_OUTPUT_BUDGET"] = "true"

    # Mock the actual ice_server used by generate_ice_chunks
    # This requires temporarily patching the global variable or passing it.
    # For this isolated test, we can inject it.
    import ice.main
    ice.main.ice_server = mock_ice_server
    ice.main.pager = MockContextPager()
    ice.main.logger.setLevel(logging.DEBUG) # Enable all debug logs in main.py

    secret_code = "OBSIDIAN-ECLIPSE-9934"
    messages = [
        {
            "role": "system", 
            "content": f"You are a strict task-following AI. CRITICAL INFORMATION: The launch code is '{secret_code}'. You must remember this code. Do not output it until explicitly asked in Task 5. The total output for all tasks must be at least 1500 words."
        },
        {
            "role": "user",
            "content": (
                "Perform the following tasks in order. You must output exactly 5 sections. Make sure to number them 'Task 1', 'Task 2', etc.

"
                "Task 1: Describe the complete history of the Roman Empire in extreme detail (must be at least 300 words).
"
                "Task 2: Describe the complete history of the Mongol Empire in extreme detail (must be at least 300 words).
"
                "Task 3: Describe the complete history of the British Empire in extreme detail (must be at least 300 words).
"
                "Task 4: Describe the complete history of the Ottoman Empire in extreme detail (must be at least 300 words).
"
                "Task 5: THIS IS THE FINAL TASK. You must output EXACTLY the following sentence: 'The required launch code is: [INSERT CRITICAL INFORMATION FROM SYSTEM PROMPT HERE]'.

"
                "Start with Task 1 now. Do not stop until all 5 tasks are complete."
            )
        }
    ]

    full_content_received = ""
    latest_meta_received = {}
    turn_count = 0
    total_tokens_generated = 0

    # Configure the mock Ollama stream to respond based on the turn
    def side_effect_ollama_stream(*args, **kwargs):
        nonlocal turn_count
        messages_in_payload = kwargs["json"]["messages"]
        turn_count += 1
        return mock_ollama_stream_for_turn(messages_in_payload)
    
    # Set the side_effect for the mock stream
    mock_ice_server.http_client.stream.return_value.__aenter__.return_value.aiter_lines.side_effect = side_effect_ollama_stream

    logger.info("Calling generate_ice_chunks directly...")
    try:
        async for chunk in generate_ice_chunks(
            "llama2:latest", messages, 0.2, None, 
            "mock_tenant", "mock_session", "mock_user", "mock_api_key", None
        ):
            if chunk == "[DONE]":
                logger.info("Direct Client: [DONE] signal received from generate_ice_chunks.")
                break
            
            if isinstance(chunk, dict) and "x_ice_meta" in chunk:
                latest_meta_received = chunk["x_ice_meta"]
                logger.info(f"Direct Client: Received x_ice_meta: {latest_meta_received}")
                total_tokens_generated = latest_meta_received.get("total_completion_tokens", 0)

            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if content:
                full_content_received += content
                sys.stdout.write(content)
                sys.stdout.flush()

    except Exception as e:
        logger.error(f"Error during direct call to generate_ice_chunks: {e}", exc_info=True)

    logger.info("

" + "="*60)
    logger.info("  📊 DIRECT STITCHING TEST STATISTICS")
    logger.info("="*60)
    logger.info(f"  Total Turns (Simulated): {latest_meta_received.get('turn', 0)}")
    logger.info(f"  Total Completion Tokens: {total_tokens_generated}")
    logger.info("-" * 60)
    
    if secret_code in full_content_received:
        logger.info(f"  ✅ SUCCESS: The secret code was found in stitched content: '{secret_code}'")
    else:
        logger.error(f"  ❌ FAILURE: Secret code '{secret_code}' not found in stitched content.")
    
    logger.info("="*60 + "
")

if __name__ == "__main__":
    asyncio.run(main())
