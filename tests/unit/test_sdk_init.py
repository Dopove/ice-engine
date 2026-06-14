import asyncio
from ice.sdk import init

async def main():
    ice = await init(license_key="TEST_LICENSE")
    print(f"Default client: {ice}")
    if ice is None:
        print("ICE is None")
    else:
        print("ICE is not None")

if __name__ == "__main__":
    asyncio.run(main())
