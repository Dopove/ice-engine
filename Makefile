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
	@echo "🐧 Building Linux (Docker) wheels..."
	mkdir -p $(OUTPUT_DIR)
	# Running via docker as the current user to avoid permission errors
	docker run --rm -v "$(PWD):/io" --user $(id -u):$(id -g) quay.io/pypa/manylinux2014_x86_64 /io/scripts/build_linux.sh

build-node:
	@echo "🟢 Building Node.js Client..."
	cd clients/node/ice-client && npm install && npx node-gyp rebuild
	mkdir -p $(OUTPUT_DIR)/node
	cp clients/node/ice-client/build/Release/*.node $(OUTPUT_DIR)/node/

build: build-linux build-node

clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV) .pytest_cache __pycache__ ice/__pycache__ $(OUTPUT_DIR) build/ *.egg-info
