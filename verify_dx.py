import asyncio
from ice.sdk import ICE

async def main():
    print("--- Verifying ICE V3 Developer Experience ---")

    # 1. Developer initializes the engine
    print("\n[1/3] Initializing ICE Engine...")
    try:
        ice = ICE()
        print("✅ SUCCESS: Engine initialized in sovereign mode.")
    except Exception as e:
        print(f"❌ FAILED: Could not initialize engine: {e}")
        return

    # 2. Developer ingests data from a URI
    print("\n[2/3] Testing Universal Data Ingestion...")
    try:
        # Create a dummy file to ingest
        with open("my_test_doc.txt", "w") as f:
            f.write("This is a test document for ICE V3 ingestion.")
        
        # Ingest the local file
        result = await ice.ingest(source="my_test_doc.txt")
        assert result["success"] is True
        print("✅ SUCCESS: Ingestion from local file URI works.")
    except Exception as e:
        print(f"❌ FAILED: Ingestion failed: {e}")

    # 3. Developer queries the engine
    print("\n[3/3] Testing Sovereign Query...")
    try:
        response = await ice.query("What was in the test document?")
        print(f"✅ SUCCESS: Query returned a response:\n'{response}'")
    except Exception as e:
        print(f"❌ FAILED: Query failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
