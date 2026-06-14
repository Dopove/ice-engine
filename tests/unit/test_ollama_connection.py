import asyncio
import ollama
import os
import sys

async def test_connection_with_env_check():
    print("--- Environment Variables Check ---")
    print(f"HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
    print(f"HTTPS_PROXY: {os.getenv('HTTPS_PROXY')}")
    print(f"NO_PROXY: {os.getenv('NO_PROXY')}")
    print(f"OLLAMA_HOST: {os.getenv('OLLAMA_HOST')}")
    print(f"UPSTREAM_API_URL: {os.getenv('UPSTREAM_API_URL')}") # From our script
    print("-----------------------------------")

    try:
        client = ollama.AsyncClient(host='http://localhost:11434')
        print("Attempting to connect to Ollama using ollama.AsyncClient...")

        models_raw = await client.list() # Get the raw response
        
        print("\n--- RAW OLLAMA MODELS RESPONSE ---")
        print(models_raw) # Print the raw response
        print("----------------------------------")

        models_list = models_raw.get('models', []) # This should be a list of dicts
        
        print("\n--- Parsed Models List ---")
        if not models_list:
            print("No models found or 'models' key missing in response.")
        for model_item in models_list: # Renamed loop variable to avoid confusion
            # Now try to safely access 'name'
            model_name = model_item.get('name', 'N/A (name key missing)')
            print(f"- {model_name}")
        print("--------------------------")
        
        print("\n--- Ollama Connection SUCCESS (Structural Check) ---")
        print("--------------------------------------------------")
        
    except Exception as e:
        print("\n--- Ollama Connection FAILED ---")
        print(f"Error: {e}")
        print("--------------------------------")
        
if __name__ == "__main__":
    asyncio.run(test_connection_with_env_check())