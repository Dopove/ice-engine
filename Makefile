.PHONY: setup test build clean build-linux build-mac build-win build-all

VENV := .venv_test
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
OUTPUT_DIR := dist

# Get current user and group IDs
USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)

setup:
	@echo "🛠️ Setting up isolated test environment..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio
	$(PIP) install -e .

test: setup
	@echo "🧪 Running test suite..."
	PYTHONPATH=. $(PYTEST) tests/unit/ -v -s

build-linux:
	@echo "🐧 Building Linux (Docker) wheels on this machine..."
	rm -rf $(OUTPUT_DIR)/linux && mkdir -p $(OUTPUT_DIR)/linux
	# Fixed: Using $(USER_ID):$(GROUP_ID) to ensure files are owned by the host user
	docker run --rm -v "$(PWD):/io" --user $(USER_ID):$(GROUP_ID) quay.io/pypa/manylinux2014_x86_64 /io/scripts/build_linux.sh

build-mac:
	@echo "🍎 Building macOS (Zig) binaries on this machine..."
	rm -rf $(OUTPUT_DIR)/macos && mkdir -p $(OUTPUT_DIR)/macos
	# Zig cross-compilation targetting macOS. Using isolated build directory.
	CC="zig cc -target x86_64-macos" CXX="zig c++ -target x86_64-macos" python3 -m build . --wheel --outdir $(OUTPUT_DIR)/macos

build-win:
	@echo "🪟 Building Windows (Docker) wheels on this machine..."
	rm -rf $(OUTPUT_DIR)/windows && mkdir -p $(OUTPUT_DIR)/windows
	# Windows cross-compilation via Docker
	docker run --rm -v "$(PWD):/io" --user $(USER_ID):$(GROUP_ID) ubuntu:latest /io/scripts/build_win.sh

build-all: build-linux build-mac build-win

clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV) .pytest_cache __pycache__ ice/__pycache__ $(OUTPUT_DIR) *.egg-info
	# Note: build/ is deliberately omitted here to avoid permission errors if previously run as root.
