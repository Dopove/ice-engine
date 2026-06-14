import httpx
import json

def test_models():
    url = "http://localhost:8008/v1/models"
    try:
        response = httpx.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print("Available Models via ICE:")
            for m in models.get("data", []):
                print(f" - {m['id']} (owned by {m['owned_by']})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed to connect to ICE Engine: {e}")

if __name__ == "__main__":
    test_models()
