import asyncio
from ice.sdk import IndexlessContextClient as ICEClient

async def run_stress_test():
    print("=== ICE Engine Integration & Stress Test ===")
    
    # Initialize the ICE SDK Client
    client = ICEClient(base_url="http://localhost:8081", api_key="stress-test-key")
    session_id = "stress-test-session-ws"
    
    # 1. Generate Massive Context (Simulating a long chat history)
    print("\\nGenerating massive history payload...")
    messages = []
    
    for i in range(100):
        messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i}: This is some filler context about project architecture. We decided to use Postgres and Redis. " * 2
        })
        
    # The final instruction asking for complex reasoning
    messages.append({
        "role": "user",
        "content": "Analyze the previously mentioned architecture. Then, output a detailed, multi-step thought process enclosed in <thought> tags outlining how to scale this system to 10 million concurrent users. Then provide the final summary."
    })
    
    print(f"Total messages sent to ICE: {len(messages)}")
    print(f"Approximate input characters: {sum(len(m['content']) for m in messages)}")
    print(f"\\nConnecting to ICE Engine WebSocket for session: {session_id}...")
    
    try:
        import time
        model = "llama3.2:latest"
        
        full_response = ""
        chunk_count = 0
        start_time = time.time()
        first_token_time = None
        
        async for chunk in client.chat_stream_ws(session_id=session_id, model=model, messages=messages):
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk
            chunk_count += 1
            if chunk_count % 20 == 0:
                print(".", end="", flush=True)
                
        end_time = time.time()
        ttft = first_token_time - start_time if first_token_time else 0
        total_time = end_time - start_time
        tps = chunk_count / total_time if total_time > 0 else 0
        approx_chars = sum(len(m['content']) for m in messages)
        
        print(f"\\n\\n[SUCCESS] Response Received!")
        print(f"--- METRICS ---")
        print(f"Input Context Size: {approx_chars} characters (~{approx_chars//4} tokens)")
        print(f"Output Size: {len(full_response)} characters")
        print(f"Time to First Token (TTFT): {ttft:.2f} seconds")
        print(f"Total Generation Time: {total_time:.2f} seconds")
        print(f"Throughput: {tps:.2f} tokens/second (assuming 1 chunk ≈ 1 token)")
        print("\\n--- Output Preview ---")
        if len(full_response) > 800:
            print(full_response[:400] + "\\n...\\n[TRUNCATED]\\n...\\n" + full_response[-400:])
        else:
            print(full_response)
        print("----------------------")
        
    except Exception as e:
        print(f"\\n[EXCEPTION]: {e}")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
