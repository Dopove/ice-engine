import pytest
import os
import socket
from unittest.mock import AsyncMock, patch, MagicMock

# Global mock for ice_server if it exists in ice.main
ice_main = None
try:
    import ice.main as _ice_main_
    ice_main = _ice_main_
except ImportError:
    pass

def is_docker_available():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)  # Shorter timeout for quick check
            # Check a common Docker port like PostgreSQL (5432) or Redis (6379)
            # if either is up, we assume Docker is generally running useful services
            return s.connect_ex(("localhost", 5432)) == 0 or s.connect_ex(("localhost", 6379)) == 0
    except Exception:
        return False

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """Force safe device settings and licensing bypass for all tests."""
    os.environ["ICE_DEVICE"] = "cpu"
    os.environ["MINERU_DEVICE"] = "cpu"
    os.environ["ICE_BYPASS_LICENSING"] = "1"
    # Ensure ICE_SKU is set for license checks
    os.environ["ICE_SKU"] = "ICE-UNLIMITED"
    
    # Patch ice.build_config.ICE_SKU if it exists and is used
    try:
        with patch('ice.build_config.ICE_SKU', 'ICE-UNLIMITED'):
            yield
    except (AttributeError, ImportError):
        # build_config might not exist or be structured differently; proceed without patching
        yield

@pytest.fixture
def mock_ice_client():
    from ice.testing.mock_client import MockClient
    return MockClient()

@pytest.fixture(scope="session")
def mock_db_pool():
    """Mocks the asyncpg database pool for isolated testing."""
    pool = AsyncMock()
    # Mock acquire to return an async context manager
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="DELETE 1") # Default for purge_data
    mock_conn.fetch = AsyncMock(return_value=[]) # Default for episodic_search

    async def mock_acquire():
        return MagicMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=None))

    pool.acquire.side_effect = mock_acquire
    return pool

@pytest.fixture(scope="session", autouse=True)
def patch_ice_server_dependencies(mock_db_pool):
    """Patches global ice_server dependencies for tests, preventing real connections."""
    if ice_main and hasattr(ice_main, 'ice_server'):
        with patch.object(ice_main.ice_server, 'db_pool', new=mock_db_pool):
            # Also patch the RAG engine if it's part of ice_server
            if hasattr(ice_main.ice_server, 'rag'):
                with patch.object(ice_main.ice_server, 'rag', new=AsyncMock()):
                    yield
            else:
                yield
    else:
        yield # Yield even if ice_main not available, so tests can run

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Skips integration tests if Docker is not running."""
    if not is_docker_available():
        skip_docker = pytest.mark.skip(reason="Live infrastructure (Docker) not available or not ready")
        for item in items:
            # Check if the test file path contains 'integration' or specific test names
            if (
                "integration" in str(item.fspath) or
                "test_community_limits.py" in str(item.fspath) or
                "test_federated_search.py" in str(item.fspath)
            ):
                item.add_marker(skip_docker)
