# SPDX-License-Identifier: MIT

import asyncio
import click
import uvicorn
import os
from .license_cli import license

@click.group()
def main():
    """ICE (Infinite Context Engine) Engine CLI"""
    pass

@main.command()
@click.option("--port", default=int(os.getenv("ICE_PORT", 8000)), help="Port to run on.")
@click.option("--host", default="0.0.0.0", help="Host to bind to.")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
def serve(port, host, reload):
    """Launch the ICE Engine."""
    click.echo(f"🧊 Launching ICE Engine v3.0.0 on {host}:{port}...")
    uvicorn.run("ice.main:app", host=host, port=port, reload=reload)

@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--session-id", required=True, help="Session ID to associate with the mounted content.")
@click.option("--user-id", default="default-user", help="User ID to associate with the mounted content.")
def mount(path, session_id, user_id):
    """
    Mounts local files or directories into the ICE Semantic Ledger, performing
    local chunking and embedding.
    """
    from .sdk import init
    click.echo(f"🧊 Mounting '{path}' for Session: '{session_id}', User: '{user_id}'...")
    
    async def _mount():
        ice_client = await init() # Initialize the ICE Kernel
        
        # The sdk.py uses x_user_id and x_session_id in ingest method.
        # Wait, let's check sdk.py
        total_chunks = await ice_client.ingest(
            file_path=path,
            session_id=session_id,
            x_user_id=user_id # Changed from user_id to x_user_id
        )
        click.echo(f"✅ Successfully mounted '{path}'.")
        # IngestionPipeline logs total_chunks internally.
    
    asyncio.run(_mount())

# Add the license command group
main.add_command(license)

if __name__ == "__main__":
    main()
