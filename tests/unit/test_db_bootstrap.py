"""Self-check for the Postgres auto-provisioning detection logic (pure functions only;
no subprocess/installer calls are exercised here)."""
import shutil
from unittest.mock import patch, MagicMock

from ice.setup_db import (
    detect_package_manager,
    is_postgres_installed,
    _PG_PACKAGE_MANAGERS,
    _resolve_provision_method,
    _docker_container_state,
    _pg_major_version,
    _ensure_pgvector_native,
)


def test_detect_package_manager_linux_apt():
    with patch("platform.system", return_value="Linux"), \
         patch("shutil.which", side_effect=lambda b: "/usr/bin/apt-get" if b == "apt-get" else None):
        assert detect_package_manager() == "apt-get"


def test_detect_package_manager_macos_brew():
    with patch("platform.system", return_value="Darwin"), \
         patch("shutil.which", side_effect=lambda b: "/opt/homebrew/bin/brew" if b == "brew" else None):
        assert detect_package_manager() == "brew"


def test_detect_package_manager_none_found():
    with patch("platform.system", return_value="Linux"), patch("shutil.which", return_value=None):
        assert detect_package_manager() is None


def test_detect_package_manager_unsupported_os():
    with patch("platform.system", return_value="Windows"):
        assert detect_package_manager() is None


def test_is_postgres_installed():
    with patch("shutil.which", side_effect=lambda b: "/usr/bin/psql" if b == "psql" else None):
        assert is_postgres_installed() is True
    with patch("shutil.which", return_value=None):
        assert is_postgres_installed() is False


def test_every_package_manager_has_install_and_start():
    for mgr, spec in _PG_PACKAGE_MANAGERS.items():
        assert spec["install"], f"{mgr} missing install command"
        assert isinstance(spec["start"], list), f"{mgr} start commands must be a list"


def test_resolve_provision_method_explicit_wins():
    assert _resolve_provision_method("docker") == "docker"
    assert _resolve_provision_method("native") == "native"
    assert _resolve_provision_method("skip") == "skip"


def test_resolve_provision_method_env_var():
    with patch.dict("os.environ", {"ICE_DB_PROVISION_METHOD": "native"}):
        assert _resolve_provision_method(None) == "native"


def test_resolve_provision_method_noninteractive_defaults_to_skip():
    with patch.dict("os.environ", {}, clear=True), patch("sys.stdin.isatty", return_value=False):
        assert _resolve_provision_method(None) == "skip"


def test_resolve_provision_method_interactive_prompts():
    with patch.dict("os.environ", {}, clear=True), \
         patch("sys.stdin.isatty", return_value=True), \
         patch("ice.setup_db.prompt_provision_method", return_value="docker") as mock_prompt:
        assert _resolve_provision_method(None) == "docker"
        mock_prompt.assert_called_once()


def test_docker_container_state_running():
    mock_result = MagicMock(returncode=0, stdout="running\n")
    with patch("subprocess.run", return_value=mock_result):
        assert _docker_container_state("ice-postgres") == "running"


def test_docker_container_state_absent():
    mock_result = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        assert _docker_container_state("ice-postgres") is None


def test_pg_major_version_parses_pg_config():
    mock_result = MagicMock(returncode=0, stdout="PostgreSQL 16.4\n")
    with patch("subprocess.run", return_value=mock_result):
        assert _pg_major_version() == "16"


def test_pg_major_version_none_when_unavailable():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert _pg_major_version() is None


def test_ensure_pgvector_native_apt_uses_detected_version():
    with patch("ice.setup_db._pg_major_version", return_value="16"), \
         patch("ice.setup_db._run", return_value=True) as mock_run:
        assert _ensure_pgvector_native("apt-get") is True
        mock_run.assert_called_once_with(["sudo", "apt-get", "install", "-y", "postgresql-16-pgvector"])


def test_ensure_pgvector_native_apt_no_version_detected():
    with patch("ice.setup_db._pg_major_version", return_value=None):
        assert _ensure_pgvector_native("apt-get") is False


def test_ensure_pgvector_native_brew():
    with patch("ice.setup_db._run", return_value=True) as mock_run:
        assert _ensure_pgvector_native("brew") is True
        mock_run.assert_called_once_with(["brew", "install", "pgvector"])


def test_ensure_pgvector_native_unsupported_manager_skips():
    for mgr in ("dnf", "yum", "zypper", "pacman", None):
        assert _ensure_pgvector_native(mgr) is False


if __name__ == "__main__":
    test_detect_package_manager_linux_apt()
    test_detect_package_manager_macos_brew()
    test_detect_package_manager_none_found()
    test_detect_package_manager_unsupported_os()
    test_is_postgres_installed()
    test_every_package_manager_has_install_and_start()
    test_resolve_provision_method_explicit_wins()
    test_resolve_provision_method_env_var()
    test_resolve_provision_method_noninteractive_defaults_to_skip()
    test_resolve_provision_method_interactive_prompts()
    test_docker_container_state_running()
    test_docker_container_state_absent()
    test_pg_major_version_parses_pg_config()
    test_pg_major_version_none_when_unavailable()
    test_ensure_pgvector_native_apt_uses_detected_version()
    test_ensure_pgvector_native_apt_no_version_detected()
    test_ensure_pgvector_native_brew()
    test_ensure_pgvector_native_unsupported_manager_skips()
    print("OK")
