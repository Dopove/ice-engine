.PHONY: setup test build clean build-linux build-node

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
	$(PIP) install pytest pytest-asyncio
	$(PIP) install -e .

test: setup
	@echo "🧪 Running test suite..."
	PYTHONPATH=. $(PYTEST) tests/unit/ -v -s

build-linux:
	@echo "🐧 Building Linux Python wheels..."
	rm -rf $(OUTPUT_DIR) && mkdir -p $(OUTPUT_DIR)
	python3 -m cibuildwheel --output-dir $(OUTPUT_DIR) .

build-node:
	@echo "🟢 Building Node.js Client..."
	cd clients/node/ice-client && npm install && npx node-gyp rebuild
	mkdir -p $(OUTPUT_DIR)/node
	cp clients/node/ice-client/build/Release/*.node $(OUTPUT_DIR)/node/

build: build-linux build-node

clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf ice/__pycache__
	rm -rf $(OUTPUT_DIR)
	rm -rf build/
	rm -rf *.egg-info
