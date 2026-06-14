import asyncio
import os
import subprocess
import sys
import time
import textwrap
import asyncpg
import redis.asyncio as redis
import signal
from contextlib import asynccontextmanager

try:
    import ollama
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.prompt import Prompt
    from rich.align import Align
    from rich.text import Text
except ImportError:
    print("Missing dependencies. Please run 'pip install ollama rich asyncpg redis psutil' first.", file=sys.stderr)
    sys.exit(1)

# Assume ice is installed and available in the environment
from ice.sdk import init as init_ice

# --- CONFIGURATION ---
CONSOLE = Console()
ICE_PORT = 8008
ICE_HOST = "127.0.0.1"
ICE_URL = f"http://{ICE_HOST}:{ICE_PORT}"
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LARGE_FILE_NAME = "large_dataset.txt"
LARGE_FILE_SIZE_MB = 50
NEEDLE = "The Sovereign Key for Project Titan is 8841-A-Delta."

# --- INFRASTRUCTURE DETAILS ---
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "ice_user"
PG_PASSWORD = "ice_password"
PG_DB = "ice_db"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

DATABASE_URL = f"postgres://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

async def check_infra_ready():
    """Checks if PostgreSQL and Redis are accessible."""
    CONSOLE.print("[dim]Checking infrastructure readiness...[/dim]")
    
    # Check PostgreSQL
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        CONSOLE.print(f"[bold green]✔[/bold green] PostgreSQL is accessible at {PG_HOST}:{PG_PORT}")
    except Exception as e:
        CONSOLE.print(f"[bold red]❌ PostgreSQL connection failed:[/bold red] {e}")
        CONSOLE.print("[bold yellow]Please ensure your PostgreSQL container is running via docker-compose (client_demos/deployment/docker).[/bold yellow]")
        return False

    # Check Redis
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        await r.ping()
        CONSOLE.print(f"[bold green]✔[/bold green] Redis is accessible at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        CONSOLE.print(f"[bold red]❌ Redis connection failed:[/bold red] {e}")
        CONSOLE.print("[bold yellow]Please ensure your Redis container is running via docker-compose (client_demos/deployment/docker).[/bold yellow]")
        return False
        
    return True

# --- LIVE METRICS & SERVER MANAGEMENT ---
@asynccontextmanager
async def live_ice_engine(): # Removed model_name param
    """Context manager to start and cleanly stop the ICE engine process."""
    process = None
    env = os.environ.copy()
    env["UPSTREAM_API_URL"] = OLLAMA_URL
    env["ICE_PORT"] = str(ICE_PORT)
    env["PYTHONPATH"] = os.path.dirname(os.getcwd()) + ":" + os.path.join(os.getcwd(), '..') + ":" + env.get("PYTHONPATH", "") # Add project root to PYTHONPATH
    
    # Crucially, pass the DB/Redis URLs to the ICE Engine subprocess
    env["DATABASE_URL"] = DATABASE_URL
    env["REDIS_URL"] = REDIS_URL
    
    cmd = [sys.executable, "-m", "uvicorn", "ice.main:app", f"--host={ICE_HOST}", f"--port={ICE_PORT}"]
    
    try:
        CONSOLE.print(f"[dim]Attempting to start live ICE Engine on port {ICE_PORT}...[/dim]")
        process = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        await asyncio.sleep(5) # Give server time to start

        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"""ICE Engine failed to start. Is port {ICE_PORT} busy?
STDOUT:
{stdout.decode()}
STDERR:
{stderr.decode()}""")
        
        CONSOLE.print(f"[bold green]✔[/bold green] Live ICE Engine process started (PID: {process.pid}).")
        yield process
    finally:
        if process:
            CONSOLE.print(f"
[dim]Shutting down ICE Engine (PID: {process.pid})...[/dim]")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass # Already dead
            CONSOLE.print("[bold red]✔[/bold red] ICE Engine shut down.")

def generate_large_file(file_path: str, size_mb: int) -> str:
    """Generates a large text file with a needle inside."""
    mb_to_bytes = size_mb * 1024 * 1024
    
    with Progress(
        TextColumn("[cyan]Generating {task.description}..."),
        BarColumn(),
        transient=True
    ) as progress:
        task = progress.add_task(f"{size_mb}MB dataset", total=mb_to_bytes)
        with open(file_path, "w") as f:
            bytes_written = 0
            
            # Write preamble
            f.write("Beginning of a very large and boring log file...

")
            bytes_written = f.tell() # Update bytes_written after initial write
            progress.update(task, completed=bytes_written)

            while bytes_written < mb_to_bytes / 2:
                chunk = f"LOG Entry: {time.time()} | System Status: OK | Component: Core Processor | Value: {os.urandom(16).hex()}
"
                f.write(chunk)
                bytes_written += len(chunk)
                progress.update(task, completed=bytes_written)

            # Write the needle
            needle_block = f"
--- CRITICAL SECURITY EVENT ---
{NEEDLE}
--- END EVENT ---

"
            f.write(needle_block)
            bytes_written += len(needle_block)
            progress.update(task, completed=bytes_written)
            
            # Write postamble
            while bytes_written < mb_to_bytes:
                chunk = f"LOG Entry: {time.time()} | System Status: OK | Component: Memory Bus | Value: {os.urandom(16).hex()}
"
                f.write(chunk)
                bytes_written += len(chunk)
                progress.update(task, completed=bytes_written)
    
    CONSOLE.print(f"[bold green]✔[/bold green] Generated `{file_path}` ({os.path.getsize(file_path) / (1024*1024):.2f}MB)")
    return file_path

def make_layout() -> Layout:
    """Defines the Rich layout."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=5, name="footer")
    )
    layout["main"].split_row(Layout(name="side"), Layout(name="body", ratio=2, minimum_size=60))
    return layout

async def run_live_demo(model_name: str, dataset_path: str):
    CONSOLE.clear()
    CONSOLE.print(Panel.fit(f"[bold white]DOPOVE ICE | Live Precision Paging Stress Test[/bold white]
[dim]Model: {model_name} | Dataset: {dataset_path}[/dim]", border_style="blue"))

    async with live_ice_engine():
        ice_client = await init_ice()
        
        # --- Phase 1: Ingestion ---
        CONSOLE.rule("[bold yellow]Phase 1: Live Ingestion[/bold yellow]")
        start_time = time.time()
        with CONSOLE.status("[bold cyan]Ingesting and vectorizing massive dataset...", spinner="earth"):
            await ice_client.ingest(file_path=dataset_path, x_user_id="live_demo_user", x_session_id="live_demo_session")
        ingest_time = time.time() - start_time
        CONSOLE.print(f"[bold green]✔[/bold green] Ingested {os.path.getsize(dataset_path) / (1024*1024):.2f}MB in [magenta]{ingest_time:.2f}s[/magenta].
")
        
        # --- Phase 2: Live Query ---
        CONSOLE.rule("[bold yellow]Phase 2: Live Precision Paging (Needle in a Haystack)[/bold yellow]")
        prompt = f'Search the entire ingested document and find the exact sentence containing the "Sovereign Key".'
        CONSOLE.print(f"[bold cyan]User:[/bold cyan] {prompt}
")
        
        ollama_client = ollama.AsyncClient(host=ICE_URL)
        
        try:
            full_response = ""
            with CONSOLE.status("[bold cyan]ICE is retrieving context and querying Ollama...", spinner="dots") as status:
                async with ollama_client.chat(
                    model=model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    stream=True
                ) as stream:
                    async for chunk in stream:
                        if 'content' in chunk['message']:
                            token = chunk['message']['content']
                            full_response += token
                            status.update(f"[bold green]Live from Ollama -> ICE:[/bold green] {full_response}")
            
            CONSOLE.print(f"[bold green]Live from Ollama -> ICE:[/bold green] {full_response}")

            if NEEDLE in full_response:
                CONSOLE.print(Panel(f"[bold green]✅ SUCCESS[/bold green]
ICE enabled the SLM to find the needle in a {os.path.getsize(dataset_path) / (1024*1024):.2f}MB dataset instantly.", title="[green]Verdict[/green]"))
            else:
                CONSOLE.print(Panel(f"[bold red]❌ FAILURE[/bold red]
The model failed to find the needle. ICE's Precision Paging pipeline might have an issue.", title="[red]Verdict[/red]"))

        except Exception as e:
            CONSOLE.print(f"[bold red]ERROR:[/bold red] An error occurred during the live query: {e}")

    os.remove(dataset_path) # Changed from LARGE_FILE_NAME
    CONSOLE.print("[bold green]✔[/bold green] Cleanup complete.")

async def main():
    CONSOLE.clear()
    
    # 0. Initial Infra Check
    if not await check_infra_ready():
        CONSOLE.print("[bold red]Please set up your infrastructure and try again.[/bold red]")
        return
        
    try:
        ollama.list()
    except Exception:
        CONSOLE.print("[bold red]ERROR: Ollama is not running.[/bold red] Please run `ollama serve` in another terminal and ensure you have models pulled (e.g., `ollama pull llama3.2:3b`).")
        return

    model = Prompt.ask("[bold cyan]Enter the Ollama model to use for the stress test[/bold cyan]", default="llama3.2:3b")
    
    dataset_path_input = Prompt.ask(
        "[bold cyan]Enter the path to your large dataset file, or press Enter to generate a 50MB test file[/bold cyan]",
        default="generate"
    )

    generated = False
    if dataset_path_input == "generate":
        actual_dataset_path = generate_large_file(LARGE_FILE_NAME, 50) # Pass filename
        generated = True
    else:
        actual_dataset_path = dataset_path_input
    
    if not os.path.exists(actual_dataset_path):
        CONSOLE.print(f"[bold red]ERROR: Dataset file not found at '{actual_dataset_path}'[/bold red]")
        return
        
    try:
        await run_live_demo(model, actual_dataset_path)
    finally:
        if generated and os.path.exists(actual_dataset_path):
            os.remove(actual_dataset_path)
            CONSOLE.print(f"[dim]Cleaned up generated file: {actual_dataset_path}[/dim]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.print("
[bold red]Exiting demo.[/bold red]")