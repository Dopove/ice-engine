import asyncio
from httpx import AsyncClient, ASGITransport
from ice.main import app, ice_server

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        print("Redis:", ice_server.redis)
        print("DB Pool:", ice_server.db_pool)
        if ice_server.db_pool:
            async with ice_server.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT COUNT(*) FROM episodic_ledger")
                print("Count in DB:", rows[0]['count'])

asyncio.run(main())
