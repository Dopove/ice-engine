.PHONY: setup test build clean build-linux build-mac build-win build-all release

VENV := .venv_test
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
OUTPUT_DIR := dist

setup:
	@echo "🛠️ Setting up isolated test environment..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r test_requirements.txt
	$(PIP) install pytest pytest-asyncio build twine
	$(PIP) install -e .

test: setup
	@echo "🧪 Running test suite..."
	PYTHONPATH=. $(PYTEST) tests/unit/ -v -s

build-linux: setup
	@echo "🐧 Building Linux wheels..."
	mkdir -p $(OUTPUT_DIR)/linux
	$(PYTHON) -m build . --wheel --outdir $(OUTPUT_DIR)/linux

build-mac: setup
	@echo "🍎 Building macOS wheels (requires Zig)..."
	mkdir -p $(OUTPUT_DIR)/macos
	$(PYTHON) -m build . --wheel --outdir $(OUTPUT_DIR)/macos

build-win:
	@echo "🪟 Building Windows wheels (run on Windows host)..."
	@echo "Note: True cross-compilation for Windows C extensions on Linux is unsupported."
	@echo "Please run 'python -m build . --wheel --outdir dist/windows' on a Windows machine."
	@exit 1

build-all: build-linux build-mac
	@echo "Finished building supported local targets."

release: build-all
	@echo "🚀 Releasing artifacts via Twine..."
	$(PYTHON) -m twine upload $(OUTPUT_DIR)/linux/* $(OUTPUT_DIR)/macos/*
	@echo "Note: Windows wheels must be uploaded separately from the Windows host."

clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV) .pytest_cache __pycache__ ice/__pycache__ $(OUTPUT_DIR) build/ *.egg-info
