import asyncio
import os
import asyncpg

# ==============================================================================
# DATA GOVERNANCE: GDPR & RIGHT TO BE FORGOTTEN
# ==============================================================================
# Because ICE stores 100B tokens of user history indefinitely, Enterprise clients
# legally require a mechanism to purge specific users or tenants completely to
# comply with GDPR, CCPA, and standard Data Deletion Requests.

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://ice_user:ice_password@localhost:5432/ice_db")

async def execute_gdpr_purge(tenant_id: str, user_id: str):
    """
    Hard-deletes all episodic memory, reasoning traces, and vector embeddings
    for a specific user within a tenant namespace.
    """
    print(f"🚨 [COMPLIANCE]: Initiating GDPR Purge for User: '{user_id}' in Tenant: '{tenant_id}'")
    
    try:
        # 1. Connect directly to the ICE Semantic Ledger
        conn = await asyncpg.connect(DATABASE_URL)
        
        # 2. Execute the Purge Transaction
        async with conn.transaction():
            
            # The 'episodic_ledger' holds all chat history and chunked document embeddings
            query = """
                DELETE FROM episodic_ledger 
                WHERE tenant_id = $1 AND user_id = $2
            """
            
            # Use safe_uuid logic if your DB schema enforces UUID constraints
            result = await conn.execute(query, tenant_id, user_id)
            
            # Extract number of rows deleted
            rows_deleted = int(result.split()[-1])
            
        print(f"✅ [COMPLIANCE]: Successfully permanently deleted {rows_deleted} semantic chunks.")
        print(f"   User '{user_id}' has been entirely wiped from the Infinite Context Engine.")
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ [ERROR]: Database authentication failed. Check DATABASE_URL.")
    except Exception as e:
        print(f"❌ [ERROR]: Purge failed: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    # Example: A user clicks "Delete My Account" on the client's frontend.
    # The client's backend triggers this internal script to wipe the ICE ledger.
    target_tenant = "00000000-0000-0000-0000-000000000000"
    target_user = "user-requiring-deletion-99"
    
    print("--- ICE Data Governance Utility ---")
    asyncio.run(execute_gdpr_purge(target_tenant, target_user))
