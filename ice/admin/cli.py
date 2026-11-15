# SPDX-License-Identifier: BSL-1.1

#!/usr/bin/env python3
"""
ICE Admin CLI
Command-line interface for ICE administration tasks.
"""

import asyncio
import json
import os
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ice.kernel import ICEKernel
from ice.telemetry import TelemetryConfig, RemoteTelemetryClient

console = Console()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.pass_context
def cli(ctx: click.Context, debug: bool):
    """ICE Admin CLI - Administration interface for ICE Indexless Context Engine."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option("--name", prompt="Tenant name", help="Tenant name")
@click.option("--tier", type=click.Choice(["community", "developer-pro", "enterprise"]), default="community", help="License tier")
@click.option("--max-tenants", default=1, help="Maximum number of tenants")
@click.option("--max-nodes", default=1, help="Maximum number of nodes")
@click.option("--max-concurrent-sessions", default=10, help="Maximum concurrent sessions")
@click.option("--max-tokens-per-session", default=10_000_000, help="Maximum tokens per session")
@click.option("--max-users", default=1, help="Maximum users")
@click.option("--telemetry-endpoint", default="", help="Telemetry endpoint URL")
@click.option("--telemetry-api-key", default="", help="Telemetry API key")
@click.pass_context
def create_tenant(ctx: click.Context, name: str, tier: str, max_tenants: int, max_nodes: int,
                  max_concurrent_sessions: int, max_tokens_per_session: int, max_users: int,
                  telemetry_endpoint: str, telemetry_api_key: str):
    """Create a new tenant with specified limits."""
    async def _create_tenant():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing ICE kernel...", total=None)

            # Initialize kernel with admin config
            kernel = ICEKernel(
                license_key=None,
                telemetry_endpoint=telemetry_endpoint or None,
                telemetry_api_key=telemetry_api_key or None,
                telemetry_enabled=bool(telemetry_endpoint)
            )
            await kernel.connect()

            try:
                # Create tenant via security manager
                from ice.core.security import SecurityManager
                security = SecurityManager()
                tenant_id = await security.create_tenant(
                    name=name,
                    tier=tier,
                    limits={
                        "max_tenants": max_tenants,
                        "max_nodes": max_nodes,
                        "max_concurrent_sessions": max_concurrent_sessions,
                        "max_tokens_per_session": max_tokens_per_session,
                        "max_users": max_users,
                    }
                )

                progress.update(task, description="Tenant created successfully!")

                # Display results
                console.print(Panel.fit(
                    f"[green]Tenant created successfully![/green]\n\n"
                    f"[bold]Tenant ID:[/bold] {tenant_id}\n"
                    f"[bold]Name:[/bold] {name}\n"
                    f"[bold]Tier:[/bold] {tier}\n"
                    f"[bold]Max Tenants:[/bold] {max_tenants}\n"
                    f"[bold]Max Nodes:[/bold] {max_nodes}\n"
                    f"[bold]Max Concurrent Sessions:[/bold] {max_concurrent_sessions}\n"
                    f"[bold]Max Tokens/Session:[/bold] {max_tokens_per_session:,}\n"
                    f"[bold]Max Users:[/bold] {max_users}",
                    title="Tenant Created"
                ))

            finally:
                await kernel.disconnect()

    asyncio.run(_create_tenant())


@cli.command()
@click.option("--tenant-id", help="Specific tenant ID to list (optional)")
@click.pass_context
def list_tenants(ctx: click.Context, tenant_id: Optional[str]):
    """List all tenants or a specific tenant."""
    async def _list_tenants():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching tenants...", total=None)

            kernel = ICEKernel()
            await kernel.connect()

            try:
                from ice.core.security import SecurityManager
                security = SecurityManager()

                if tenant_id:
                    tenant = await security.get_tenant(tenant_id)
                    if tenant:
                        console.print(Panel.fit(
                            f"[bold]Tenant ID:[/bold] {tenant['tenant_id']}\n"
                            f"[bold]Name:[/bold] {tenant['name']}\n"
                            f"[bold]Tier:[/bold] {tenant['tier']}\n"
                            f"[bold]Status:[/bold] {tenant['status']}\n"
                            f"[bold]Created:[/bold] {tenant['created_at']}",
                            title=f"Tenant: {tenant['name']}"
                        ))
                    else:
                        console.print(f"[red]Tenant {tenant_id} not found[/red]")
                else:
                    tenants = await security.list_tenants()
                    if not tenants:
                        console.print("[yellow]No tenants found[/yellow]")
                        return

                    table = Table(title="ICE Tenants")
                    table.add_column("Tenant ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Tier", style="yellow")
                    table.add_column("Status", style="magenta")
                    table.add_column("Created", style="blue")

                    for tenant in tenants:
                        table.add_row(
                            tenant['tenant_id'][:8] + "...",
                            tenant['name'],
                            tenant['tier'],
                            tenant['status'],
                            str(tenant['created_at'])[:19]
                        )

                    console.print(table)

            finally:
                await kernel.disconnect()

    asyncio.run(_list_tenants())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID to delete")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@click.pass_context
def delete_tenant(ctx: click.Context, tenant_id: str, force: bool):
    """Delete a tenant and all associated data."""
    if not force:
        if not click.confirm(f"[red]This will permanently delete tenant {tenant_id} and ALL its data. Continue?[/red]"):
            console.print("[yellow]Aborted[/yellow]")
            return

    async def _delete_tenant():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting tenant...", total=None)

            kernel = ICEKernel()
            await kernel.connect()

            try:
                from ice.core.security import SecurityManager
                security = SecurityManager()

                success = await security.delete_tenant(tenant_id)

                if success:
                    progress.update(task, description="Tenant deleted successfully!")
                    console.print(f"[green]Tenant {tenant_id} deleted successfully[/green]")
                else:
                    console.print(f"[red]Failed to delete tenant {tenant_id}[/red]")

            finally:
                await kernel.disconnect()

    asyncio.run(_delete_tenant())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID to generate API key for")
@click.option("--name", help="API key name/description")
@click.option("--expires-days", default=365, help="Expiration in days")
@click.pass_context
def generate_api_key(ctx: click.Context, tenant_id: str, name: Optional[str], expires_days: int):
    """Generate a new API key for a tenant."""
    async def _generate_key():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating API key...", total=None)

            kernel = ICEKernel()
            await kernel.connect()

            try:
                from ice.core.security import SecurityManager
                security = SecurityManager()

                api_key = await security.generate_api_key(
                    tenant_id=tenant_id,
                    name=name or f"api-key-{tenant_id[:8]}",
                    expires_days=expires_days
                )

                progress.update(task, description="API key generated!")

                console.print(Panel.fit(
                    f"[green]API Key Generated![/green]\n\n"
                    f"[bold]API Key:[/bold] {api_key}\n"
                    f"[bold]Tenant ID:[/bold] {tenant_id}\n"
                    f"[bold]Name:[/bold] {name or 'auto-generated'}\n"
                    f"[bold]Expires:[/bold] {expires_days} days\n\n"
                    f"[yellow]IMPORTANT:[/yellow] Save this key securely. It will not be shown again.",
                    title="API Key Created"
                ))

            finally:
                await kernel.disconnect()

    asyncio.run(_generate_key())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID to list API keys for")
@click.pass_context
def list_api_keys(ctx: click.Context, tenant_id: str):
    """List all API keys for a tenant."""
    async def _list_keys():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching API keys...", total=None)

            kernel = ICEKernel()
            await kernel.connect()

            try:
                from ice.core.security import SecurityManager
                security = SecurityManager()

                keys = await security.list_api_keys(tenant_id)

                if not keys:
                    console.print("[yellow]No API keys found for this tenant[/yellow]")
                    return

                table = Table(title=f"API Keys for Tenant {tenant_id[:8]}...")
                table.add_column("Key ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Created", style="blue")
                table.add_column("Expires", style="yellow")
                table.add_column("Status", style="magenta")

                for key in keys:
                    table.add_row(
                        key['key_id'][:16] + "...",
                        key['name'],
                        str(key['created_at'])[:19],
                        str(key['expires_at'])[:19] if key['expires_at'] else "Never",
                        "Active" if key['active'] else "Revoked"
                    )

                console.print(table)

            finally:
                await kernel.disconnect()

    asyncio.run(_list_keys())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID")
@click.option("--key-id", required=True, help="API Key ID to revoke")
@click.option("--force", is_flag=True, help="Force revocation without confirmation")
@click.pass_context
def revoke_api_key(ctx: click.Context, tenant_id: str, key_id: str, force: bool):
    """Revoke an API key."""
    if not force:
        if not click.confirm(f"[red]Revoke API key {key_id}? This cannot be undone.[/red]"):
            console.print("[yellow]Aborted[/yellow]")
            return

    async def _revoke_key():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Revoking API key...", total=None)

            kernel = ICEKernel()
            await kernel.connect()

            try:
                from ice.core.security import SecurityManager
                security = SecurityManager()

                success = await security.revoke_api_key(tenant_id, key_id)

                if success:
                    progress.update(task, description="API key revoked!")
                    console.print(f"[green]API key revoked successfully[/green]")
                else:
                    console.print(f"[red]Failed to revoke API key[/red]")

            finally:
                await kernel.disconnect()

    asyncio.run(_revoke_key())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID")
@click.option("--output", type=click.Choice(["json", "csv"]), default="json", help="Export format")
@click.option("--output-file", type=click.Path(), help="Output file path (default: stdout)")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.pass_context
def export_telemetry(ctx: click.Context, tenant_id: str, output: str, output_file: Optional[str],
                     start_date: Optional[str], end_date: Optional[str]):
    """Export telemetry data for a tenant (GDPR compliance)."""
    async def _export():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Exporting telemetry data...", total=None)

            from ice.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            params = {"tenant_id": tenant_id}
            if start_date:
                params["start"] = start_date
            if end_date:
                params["end"] = end_date

            response = client.get("/v1/telemetry/export", params=params)

            if response.status_code == 200:
                data = response.json()

                if output == "json":
                    import json
                    output_data = json.dumps(data, indent=2, default=str)
                else:
                    import csv
                    import io
                    output_buffer = io.StringIO()
                    writer = csv.writer(output_buffer)
                    writer.writerow(["timestamp", "event_type", "tenant_id", "session_id", "user_id", "details"])
                    for event in data.get("events", []):
                        writer.writerow([
                            event.get("timestamp", ""),
                            event.get("event_type", ""),
                            event.get("tenant_id", ""),
                            event.get("session_id", ""),
                            event.get("user_id", ""),
                            json.dumps(event.get("details", {}))
                        ])
                    output_data = output_buffer.getvalue()

                if output_file:
                    with open(output_file, "w") as f:
                        f.write(output_data)
                    console.print(f"[green]Exported to {output_file}[/green]")
                else:
                    console.print(output_data)
            else:
                console.print(f"[red]Export failed: {response.status_code} - {response.text}[/red]")

    asyncio.run(_export())


@cli.command()
@click.option("--tenant-id", required=True, help="Tenant ID to delete data for")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@click.pass_context
def delete_telemetry(ctx: click.Context, tenant_id: str, force: bool):
    """Delete all telemetry data for a tenant (GDPR right to be forgotten)."""
    if not force:
        if not click.confirm(f"[red]This will PERMANENTLY DELETE all telemetry data for tenant {tenant_id}. Continue?[/red]"):
            console.print("[yellow]Aborted[/yellow]")
            return

    async def _delete():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting telemetry data...", total=None)

            from ice.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)
            response = client.delete(f"/v1/telemetry/data?tenant_id={tenant_id}")

            if response.status_code == 200:
                progress.update(task, description="Telemetry data deleted!")
                console.print(f"[green]Telemetry data for tenant {tenant_id} deleted[/green]")
            else:
                console.print(f"[red]Deletion failed: {response.status_code} - {response.text}[/red]")

    asyncio.run(_delete())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--workers", default=1, type=int, help="Number of worker processes")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development)")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, workers: int, reload: bool):
    """Start the ICE server."""
    import uvicorn

    console.print(Panel.fit(
        f"[bold]Starting ICE Server[/bold]\n\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Workers: {workers}\n"
        f"Reload: {reload}",
        title="ICE Server"
    ))

    import uvicorn
    uvicorn.run(
        "ice.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )


@cli.command()
@click.option("--license-key", envvar="ICE_LICENSE_KEY", help="License key (or set ICE_LICENSE_KEY env var)")
@click.option("--db-url", envvar="DATABASE_URL", help="PostgreSQL connection URL")
@click.option("--redis-url", envvar="REDIS_URL", help="Redis connection URL")
@click.option("--telemetry-endpoint", envvar="ICE_TELEMETRY_ENDPOINT", help="Telemetry endpoint URL")
@click.option("--telemetry-api-key", envvar="ICE_TELEMETRY_API_KEY", help="Telemetry API key")
@click.pass_context
def init(ctx: click.Context, license_key: Optional[str], db_url: Optional[str],
         redis_url: Optional[str], telemetry_endpoint: Optional[str], telemetry_api_key: Optional[str]):
    """Initialize ICE kernel (for testing/setup)."""
    async def _init():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing ICE kernel...", total=None)

            kernel = ICEKernel(
                license_key=license_key,
                db_url=db_url,
                redis_url=redis_url,
                telemetry_endpoint=telemetry_endpoint,
                telemetry_api_key=telemetry_api_key
            )

            await kernel.connect()
            progress.update(task, description="Kernel connected!")

            health = await kernel.health()
            console.print(Panel.fit(
                f"[green]Kernel initialized successfully![/green]\n\n"
                f"Database: {health['database']}\n"
                f"Redis: {health['redis']}",
                title="Kernel Status"
            ))

            await kernel.disconnect()

    asyncio.run(_init())


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()