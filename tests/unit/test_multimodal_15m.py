import asyncio
import json
import time
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stress_test")

ICE_URL = "http://localhost:8081/v1/chat/completions"
HEADERS = {
    "Authorization": "Bearer test-api-key",
    "X-Session-Id": "multimodal-stress-test"
}

# 10M-15M Tokens is huge. 
# We simulate a "client" that sends a rapidly growing conversation history.
# We will do concurrent workers. Each worker sends increasingly large payloads.

# A single base64 image (small)
DUMMY_B64_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def generate_multimodal_message(iteration: int) -> dict:
    """Generate a large multimodal message representing roughly 10k tokens (40k chars) + images."""
    large_text = f"Synthetic RAG Text for iteration {iteration}. " * 1000  # Approx 40k chars = 10k tokens
    
    # 5 images per message
    content = [{"type": "text", "text": large_text}]
    for _ in range(5):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{DUMMY_B64_IMAGE}"
            }
        })
        
    return {
        "role": "user",
        "content": content
    }

async def send_payload(client: httpx.AsyncClient, session_id: str, messages: list):
    headers = HEADERS.copy()
    headers["X-Session-Id"] = session_id
    
    payload = {
        "model": "ministral-3:3b",
        "messages": messages,
        "temperature": 0.5
    }
    
    try:
        start_time = time.time()
        # High timeout to prevent client-side dropping while ICE digests the giant JSON
        response = await client.post(ICE_URL, json=payload, headers=headers, timeout=120.0)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return True, elapsed, data
        else:
            logger.error(f"Error {response.status_code}: {response.text}")
            return False, elapsed, None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return False, 0.0, None

async def worker(worker_id: int, total_requests: int):
    """
    Each worker builds a conversation history, pushing it to ICE.
    The history grows with each request.
    """
    session_id = f"stress-test-session-{worker_id}"
    messages = []
    
    async with httpx.AsyncClient() as client:
        for i in range(total_requests):
            # Append new huge message
            messages.append(generate_multimodal_message(i))
            
            # Estimate tokens sent
            # 10k text + 5 images (*255) = ~11,275 tokens per message
            total_tokens = len(messages) * 11275
            
            # Send to ICE
            logger.info(f"Worker {worker_id} | Req {i+1}/{total_requests} | Sending {len(messages)} messages (~{total_tokens:,} tokens) to ICE...")
            success, elapsed, data = await send_payload(client, session_id, messages)
            
            if success:
                usage = data.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                logger.info(f"Worker {worker_id} | SUCCESS ({elapsed:.2f}s) | ICE Output Tokens -> prompt: {prompt_tokens}, completion: {completion_tokens}")
            
            # To avoid overloading the SLM queue completely and failing the test just purely on Ollama queue wait time,
            # we will sleep slightly.
            await asyncio.sleep(2)

async def main():
    logger.info("Starting Multimodal 15M Token Stress Test")
    
    # We want 15,000,000 tokens total processed by the engine interface.
    # Each message is ~11,275 tokens.
    # If a worker sends 10 requests, it sends:
    # Req 1: 1 msg (11k tokens)
    # Req 2: 2 msgs (22k tokens)
    # ...
    # Req 20: 20 msgs (225k tokens)
    # Total tokens sent by 1 worker over 20 requests = sum(1 to 20) * 11k = 210 * 11,275 = 2.3M tokens.
    # 7 concurrent workers * 2.3M = ~16.5M tokens.
    
    WORKERS = 7
    REQUESTS_PER_WORKER = 20
    
    start_time = time.time()
    
    tasks = []
    for w in range(WORKERS):
        tasks.append(worker(w, REQUESTS_PER_WORKER))
        
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    logger.info(f"Stress test finished in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())
