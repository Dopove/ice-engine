# SPDX-License-Identifier: BSL-1.1

import asyncio
import click
import uvicorn
import os
import subprocess
import sys

@click.group()
def main():
    """ICE (Indexless Context Engine) Engine CLI"""
    pass


@main.command()
@click.pass_context
def help(ctx):
    """List all available commands."""
    click.echo(ctx.parent.get_help())

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

@main.group()
def db():
    """Database management commands."""
    pass


@db.command("update")
@click.option(
    "--auto-provision/--no-auto-provision", default=True,
    help="Install/start Postgres automatically if it isn't reachable (asks how, when run interactively).",
)
def db_update(auto_provision):
    """Ensure Postgres is reachable and apply/update the ICE schema (tables, extension, indexes)."""
    from .setup_db import ensure_postgres_available, setup as apply_schema

    async def _update():
        if not await ensure_postgres_available(auto_provision=auto_provision):
            click.echo("❌ Could not reach or provision Postgres. See instructions above.", err=True)
            raise SystemExit(1)
        await apply_schema()
        click.echo("✅ Database schema is up to date.")

    asyncio.run(_update())


@main.command("self-update")
@click.option("--pre", is_flag=True, help="Include pre-release versions.")
def self_update(pre):
    """Upgrade the installed ice-engine package via pip."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if pre:
        cmd.append("--pre")
    cmd.append("ice-engine")
    click.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
