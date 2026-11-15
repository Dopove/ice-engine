# SPDX-License-Identifier: MIT

import asyncio
import asyncpg
import os
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://ice_user:ice_password@localhost:5432/ice_db")
DEFAULT_TENANT_ID = "823dc24a-885e-4586-a74b-9144dcc0f849"

async def setup():
    print(f"Connecting to {DATABASE_URL}...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Enable the vector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ PostgreSQL 'vector' extension ensured.")

        # Create tenants table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_key VARCHAR(255) UNIQUE NOT NULL,
                sku VARCHAR(255), -- New column for SKU
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ 'tenants' table ensured.")

        # Add sku column if it doesn't exist (for schema evolution in existing deployments)
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='sku') THEN
                    ALTER TABLE tenants ADD COLUMN sku VARCHAR(255);
                END IF;
            END
            $$;
        """)
        print("✅ 'sku' column ensured in 'tenants' table.")

        # Create episodic_ledger table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_ledger (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                thread_id VARCHAR(255),
                role VARCHAR(255) NOT NULL,
                content TEXT,
                embedding VECTOR(384),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,                CONSTRAINT fk_tenant
                    FOREIGN KEY(tenant_id) 
                    REFERENCES tenants(tenant_id)
                    ON DELETE CASCADE
            )
        """)
        print("✅ 'episodic_ledger' table ensured.")

        # Create reasoning_traces table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_traces (
                id UUID PRIMARY KEY,
                tenant_id UUID NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                thread_id VARCHAR(255), -- New column
                content TEXT NOT NULL,
                embedding VECTOR(384), -- New column
                step_number INTEGER, -- New column
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_tenant
                    FOREIGN KEY(tenant_id) 
                    REFERENCES tenants(tenant_id)
                    ON DELETE CASCADE
            )
        """)
        print("✅ 'reasoning_traces' table ensured.")

        # Add new columns to reasoning_traces table if they don't exist (for schema evolution)
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='reasoning_traces' AND column_name='thread_id') THEN
                    ALTER TABLE reasoning_traces ADD COLUMN thread_id VARCHAR(255);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='reasoning_traces' AND column_name='embedding') THEN
                    ALTER TABLE reasoning_traces ADD COLUMN embedding VECTOR(384);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='reasoning_traces' AND column_name='step_number') THEN
                    ALTER TABLE reasoning_traces ADD COLUMN step_number INTEGER;
                END IF;
            END
            $$;
        """)
        print("✅ 'thread_id', 'embedding', 'step_number' columns ensured in 'reasoning_traces' table.")
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_tenant_session_user ON episodic_ledger (tenant_id, session_id, user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reasoning_tenant_session_user ON reasoning_traces (tenant_id, session_id, user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_created_at ON episodic_ledger (created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reasoning_created_at ON reasoning_traces (created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reasoning_embedding ON reasoning_traces USING hnsw (embedding vector_cosine_ops)") # New index
        print("✅ Indexes ensured.")

        # Create default tenant if not exists
        row = await conn.fetchrow("SELECT tenant_id FROM tenants WHERE tenant_id = $1", uuid.UUID(DEFAULT_TENANT_ID))
        if not row:
            print(f"Creating default tenant {DEFAULT_TENANT_ID}...")
            await conn.execute(
                "INSERT INTO tenants (tenant_id, name, api_key, sku) VALUES ($1, $2, $3, $4)",
                uuid.UUID(DEFAULT_TENANT_ID), "Local Developer", "ice-default-key", "ICE-DEVELOPMENT" # Insert default SKU
            )
            print("Default tenant created.")
        else:
            print("Default tenant already exists.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup())
