import logging
logger = logging.getLogger("ice_governance")
async def purge_data(tenant_id: str, user_id: str = None, db_pool=None):
    if not db_pool: logger.error("Governance purge requires an active db_pool."); raise ValueError("db_pool is required.")
    logger.warning(f"🚨 INITIATING PURGE for Tenant: {tenant_id}, User: {user_id or 'ALL'}")
    try:
        async with db_pool.acquire() as conn:
            if user_id: result = await conn.execute("DELETE FROM episodic_ledger WHERE tenant_id = $1 AND user_id = $2", tenant_id, user_id)
            else: result = await conn.execute("DELETE FROM episodic_ledger WHERE tenant_id = $1", tenant_id)
            rows_deleted = int(result.split()[-1]) if result else 0
            logger.info(f"✅ PURGE COMPLETE: Deleted {rows_deleted} vectors/chunks."); return {"status": "success", "deleted_chunks": rows_deleted}
    except Exception as e: logger.error(f"❌ PURGE FAILED: {str(e)}"); raise
