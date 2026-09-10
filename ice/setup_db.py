import asyncio
import asyncpg
import os
import platform
import shutil
import subprocess
import sys
import uuid
import logging
from urllib.parse import urlparse

logger = logging.getLogger("ice_db_bootstrap")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://ice_user:ice_password@localhost:5432/ice_db")
DEFAULT_TENANT_ID = "823dc24a-885e-4586-a74b-9144dcc0f849"

ICE_DB_NAME = os.getenv("ICE_DB_NAME", "ice_db")
ICE_DB_USER = os.getenv("ICE_DB_USER", "ice_user")
ICE_DB_PASSWORD = os.getenv("ICE_DB_PASSWORD", "ice_password")
ICE_DOCKER_PG_CONTAINER = os.getenv("ICE_DOCKER_PG_CONTAINER", "ice-postgres")
# pgvector/pgvector ships Postgres + the 'vector' extension setup_db.setup() requires;
# a plain postgres:16 image would need CREATE EXTENSION vector to fail loudly instead.
ICE_DOCKER_PG_IMAGE = os.getenv("ICE_DOCKER_PG_IMAGE", "pgvector/pgvector:pg16")

# Package manager -> (install cmd, [service-start cmds...])
# ponytail: covers the realistic dev boxes (Debian/Ubuntu, Fedora/RHEL, Arch, macOS).
# Windows/other distros fall through to manual instructions.
_PG_PACKAGE_MANAGERS = {
    "apt-get": {
        "install": ["sudo", "apt-get", "install", "-y", "postgresql"],
        "start": [["sudo", "systemctl", "enable", "--now", "postgresql"]],
    },
    "dnf": {
        "install": ["sudo", "dnf", "install", "-y", "postgresql-server", "postgresql-contrib"],
        "start": [
            ["sudo", "postgresql-setup", "--initdb"],
            ["sudo", "systemctl", "enable", "--now", "postgresql"],
        ],
    },
    "yum": {
        "install": ["sudo", "yum", "install", "-y", "postgresql-server", "postgresql-contrib"],
        "start": [
            ["sudo", "postgresql-setup", "--initdb"],
            ["sudo", "systemctl", "enable", "--now", "postgresql"],
        ],
    },
    "pacman": {
        "install": ["sudo", "pacman", "-S", "--noconfirm", "postgresql"],
        "start": [
            ["sudo", "-u", "postgres", "initdb", "-D", "/var/lib/postgres/data"],
            ["sudo", "systemctl", "enable", "--now", "postgresql"],
        ],
    },
    "zypper": {
        "install": ["sudo", "zypper", "install", "-y", "postgresql-server"],
        "start": [["sudo", "systemctl", "enable", "--now", "postgresql"]],
    },
    "brew": {
        "install": ["brew", "install", "postgresql@16"],
        "start": [["brew", "services", "start", "postgresql@16"]],
    },
}

# pgvector on a native install: reliable, well-documented packages only.
# apt/brew have a real pgvector package; dnf/yum need the PGDG repo enabled
# first (not something we auto-add) and pacman has no official package (AUR
# only) -- for those we skip auto-install and point at manual instructions
# instead of half-automating something that needs sudo + a third-party repo.
_PGVECTOR_APT_PACKAGE = "postgresql-{ver}-pgvector"
_PGVECTOR_MANUAL_NOTE = {
    "dnf": "enable the PGDG repo, then: sudo dnf install pgvector_<pg-version>",
    "yum": "enable the PGDG repo, then: sudo yum install pgvector_<pg-version>",
    "zypper": "check your distro's PGDG-equivalent repo for a pgvector package",
    "pacman": "install from the AUR, e.g.: yay -S pgvector (no official repo package)",
}


def detect_package_manager() -> str | None:
    """Pure detection logic, no side effects -- kept separate so it's unit-testable."""
    system = platform.system()
    if system == "Darwin":
        return "brew" if shutil.which("brew") else None
    if system == "Linux":
        for mgr in ("apt-get", "dnf", "yum", "pacman", "zypper"):
            if shutil.which(mgr):
                return mgr
    return None


def is_postgres_installed() -> bool:
    return shutil.which("psql") is not None or shutil.which("postgres") is not None


def is_docker_available() -> bool:
    """True if the docker CLI is present AND the daemon actually responds."""
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _print_manual_instructions(mgr: str | None):
    print(
        "\n[ICE] Could not reach Postgres and could not auto-provision it.\n"
        "Install and start Postgres yourself, then create the ICE role/database, e.g.:\n\n"
        "  Docker:\n"
        f"    docker run -d --name {ICE_DOCKER_PG_CONTAINER} \\\n"
        f"      -e POSTGRES_USER={ICE_DB_USER} -e POSTGRES_PASSWORD={ICE_DB_PASSWORD} -e POSTGRES_DB={ICE_DB_NAME} \\\n"
        f"      -p 5432:5432 -v ice_postgres_data:/var/lib/postgresql/data {ICE_DOCKER_PG_IMAGE}\n\n"
        "  Native:\n"
        "    sudo apt-get install postgresql   # or: brew install postgresql@16 / dnf install postgresql-server\n"
        f"    sudo -u postgres psql -c \"CREATE ROLE {ICE_DB_USER} WITH LOGIN PASSWORD '{ICE_DB_PASSWORD}';\"\n"
        f"    sudo -u postgres psql -c \"CREATE DATABASE {ICE_DB_NAME} OWNER {ICE_DB_USER};\"\n\n"
        "  pgvector (native installs don't ship it by default):\n"
        "    apt:    sudo apt-get install postgresql-<version>-pgvector\n"
        "    brew:   brew install pgvector\n"
        "    dnf/yum: enable the PGDG repo, then install pgvector_<pg-version>\n"
        "    pacman: no official package -- install from the AUR, e.g. 'yay -S pgvector'\n\n"
        "Or point DATABASE_URL at an existing Postgres instance (managed/remote).\n"
        "Set ICE_SKIP_INFRA_CONNECT=1 to boot ICE without a database (degraded mode).\n"
    )


def _run(cmd: list[str], timeout: int = 300) -> bool:
    logger.info(f"[ICE DB Bootstrap] Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"[ICE DB Bootstrap] Command failed: {' '.join(cmd)} -> {e}")
        return False


def prompt_provision_method() -> str:
    """
    Asks the developer how they want Postgres provisioned. Only meaningful when
    stdin is an interactive TTY -- callers should check that (or just call this
    only when they already know they're interactive) before relying on the prompt.
    Returns 'docker', 'native', or 'skip'.
    """
    print(
        "\n[ICE] PostgreSQL is required and isn't reachable.\n"
        "How would you like it provisioned?\n"
        "  [1] Docker container (isolated, easiest to remove later)\n"
        "  [2] Native install via your OS package manager\n"
        "  [3] Skip -- I'll set it up myself\n"
    )
    choice = input("Choice [1/2/3, default 1]: ").strip() or "1"
    return {"1": "docker", "2": "native", "3": "skip"}.get(choice, "docker")


def _resolve_provision_method(explicit: str | None) -> str:
    if explicit in ("docker", "native", "skip"):
        return explicit
    env_choice = os.getenv("ICE_DB_PROVISION_METHOD")
    if env_choice in ("docker", "native", "skip"):
        return env_choice
    if sys.stdin.isatty():
        return prompt_provision_method()
    # Non-interactive (CI, a daemonized server, etc.) -- don't guess, don't install.
    return "skip"


def _docker_container_state(name: str) -> str | None:
    """Returns the container's State (running/exited/...) or None if it doesn't exist."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", name],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _provision_via_docker(database_url: str) -> bool:
    if not is_docker_available():
        print("[ICE] Docker isn't installed or the daemon isn't running.")
        return False

    port = urlparse(database_url).port or 5432
    state = _docker_container_state(ICE_DOCKER_PG_CONTAINER)

    if state == "running":
        return True
    if state is not None:
        print(f"[ICE] Starting existing Docker container '{ICE_DOCKER_PG_CONTAINER}'...")
        return _run(["docker", "start", ICE_DOCKER_PG_CONTAINER])

    print(f"[ICE] Starting Postgres in Docker ({ICE_DOCKER_PG_IMAGE})...")
    return _run([
        "docker", "run", "-d", "--name", ICE_DOCKER_PG_CONTAINER,
        "-e", f"POSTGRES_USER={ICE_DB_USER}",
        "-e", f"POSTGRES_PASSWORD={ICE_DB_PASSWORD}",
        "-e", f"POSTGRES_DB={ICE_DB_NAME}",
        "-p", f"{port}:5432",
        "-v", "ice_postgres_data:/var/lib/postgresql/data",
        ICE_DOCKER_PG_IMAGE,
    ])


def _create_role_and_db() -> bool:
    """Best-effort role/database creation via the postgres superuser (peer auth on Linux)."""
    sql = (
        f"DO $$ BEGIN "
        f"IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{ICE_DB_USER}') THEN "
        f"CREATE ROLE {ICE_DB_USER} WITH LOGIN PASSWORD '{ICE_DB_PASSWORD}'; END IF; END $$;"
    )
    ok = _run(["sudo", "-u", "postgres", "psql", "-c", sql]) or _run(["psql", "-U", "postgres", "-c", sql])
    ok = _run(["sudo", "-u", "postgres", "psql", "-c",
               f"SELECT 1 FROM pg_database WHERE datname = '{ICE_DB_NAME}'"]) or ok
    _run(["sudo", "-u", "postgres", "psql", "-c", f"CREATE DATABASE {ICE_DB_NAME} OWNER {ICE_DB_USER};"])
    return ok


def _pg_major_version() -> str | None:
    """Best-effort detection of the installed Postgres major version, e.g. '16'."""
    for cmd in (["pg_config", "--version"], ["psql", "--version"]):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # "PostgreSQL 16.4" or "psql (PostgreSQL) 16.4" -> "16"
                for token in result.stdout.split():
                    if token[0].isdigit():
                        return token.split(".")[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def _ensure_pgvector_native(mgr: str | None) -> bool:
    """
    Best-effort pgvector install for the native path. Only attempted for
    package managers with a reliable, official pgvector package (apt, brew);
    dnf/yum need a third-party repo (PGDG) and pacman has no official package
    at all (AUR only) -- auto-installing those would mean silently adding a
    repo or reaching outside the distro's package manager, so we skip both
    and just point at manual instructions instead.
    """
    if mgr == "apt-get":
        ver = _pg_major_version()
        if not ver:
            print("[ICE] Could not detect installed Postgres version; skipping pgvector auto-install.")
            return False
        pkg = _PGVECTOR_APT_PACKAGE.format(ver=ver)
        print(f"[ICE] Installing {pkg}...")
        return _run(["sudo", "apt-get", "install", "-y", pkg])
    if mgr == "brew":
        print("[ICE] Installing pgvector via brew...")
        return _run(["brew", "install", "pgvector"])

    note = _PGVECTOR_MANUAL_NOTE.get(mgr, "install pgvector manually for your platform")
    print(f"[ICE] pgvector isn't auto-installable via {mgr} -- {note}")
    return False


def _provision_via_native() -> bool:
    mgr = detect_package_manager()
    if not is_postgres_installed():
        if not mgr:
            print("[ICE] No supported package manager found (apt-get/dnf/yum/pacman/zypper/brew).")
            return False
        print(f"[ICE] Installing PostgreSQL via {mgr}...")
        if not _run(_PG_PACKAGE_MANAGERS[mgr]["install"]):
            return False
        for cmd in _PG_PACKAGE_MANAGERS[mgr]["start"]:
            _run(cmd)
    elif mgr:
        # Installed but not reachable -- most likely the service isn't running yet.
        for cmd in _PG_PACKAGE_MANAGERS[mgr]["start"]:
            _run(cmd)
    _create_role_and_db()
    _ensure_pgvector_native(mgr)  # best-effort; setup() will error clearly if this didn't work
    return True


async def _can_connect(database_url: str, timeout: float = 3.0) -> bool:
    try:
        conn = await asyncio.wait_for(asyncpg.connect(database_url), timeout=timeout)
        await conn.close()
        return True
    except Exception:
        return False


async def _wait_for_connect(database_url: str, attempts: int = 15, delay: float = 2.0) -> bool:
    for _ in range(attempts):
        if await _can_connect(database_url):
            return True
        await asyncio.sleep(delay)
    return False


async def ensure_postgres_available(
    database_url: str = None, auto_provision: bool = True, method: str | None = None
) -> bool:
    """
    Checks whether Postgres is reachable at database_url (defaults to the module-level
    DATABASE_URL, i.e. the DATABASE_URL env var). If not and auto_provision is set,
    provisions it -- via Docker or a native OS package-manager install, developer's
    choice. Method resolution order: the `method` argument, then ICE_DB_PROVISION_METHOD
    ('docker'/'native'/'skip'), then an interactive prompt if stdin is a TTY, then
    'skip' (never guesses/installs unattended). Returns True if Postgres is reachable
    when this returns.

    ponytail: single-host, best-effort provisioning; no retry/backoff tuning beyond a
    flat poll, no cross-distro edge cases beyond the package managers/image above.
    Upgrade path: a real provisioning tool (Ansible/cloud-init/Testcontainers) once
    this needs to support more than "get a local dev box working".
    """
    database_url = database_url or DATABASE_URL
    if await _can_connect(database_url):
        return True

    print(f"[ICE] Postgres not reachable at {database_url}.")

    if not auto_provision:
        _print_manual_instructions(detect_package_manager())
        return False

    chosen = _resolve_provision_method(method)
    if chosen == "skip":
        _print_manual_instructions(detect_package_manager())
        return False

    provisioned = _provision_via_docker(database_url) if chosen == "docker" else _provision_via_native()
    if not provisioned:
        _print_manual_instructions(detect_package_manager())
        return False

    # Docker containers take a moment to accept connections; native services are
    # usually immediate but a short poll doesn't hurt.
    if await _wait_for_connect(database_url):
        print("[ICE] Postgres is now reachable.")
        return True

    print("[ICE] Still could not reach Postgres after provisioning.")
    _print_manual_instructions(detect_package_manager())
    return False

async def setup():
    print(f"Connecting to {DATABASE_URL}...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Enable the vector extension
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except asyncpg.PostgresError as e:
            raise RuntimeError(
                "Could not enable the 'vector' extension (pgvector) -- it isn't installed on this "
                f"Postgres server. If you provisioned via Docker this shouldn't happen; on a native "
                "install, see the pgvector instructions ensure_postgres_available() printed, or install "
                "it manually (e.g. postgresql-<version>-pgvector on apt, 'brew install pgvector' on "
                f"macOS). Original error: {e}"
            ) from e
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
