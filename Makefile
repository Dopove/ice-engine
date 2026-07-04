.PHONY: build-all build-linux build-mac build-win clean test

OUTPUT_DIR := dist
# Use a unified approach for artifacts
build-all: clean build-linux build-mac build-win

build-linux:
	@echo "🐧 Building Linux (Docker) wheels..."
	mkdir -p $(OUTPUT_DIR)
	# Running via docker for consistent Linux builds
	docker run --rm -v "$(PWD):/io" quay.io/pypa/manylinux2014_x86_64 /io/scripts/build_linux.sh

build-mac:
	@echo "🍎 Building macOS (Zig/cibuildwheel) binaries..."
	# Assuming Zig is installed and configured for cross-compilation
	export CC="zig cc -target x86_64-macos-none"
	export CXX="zig c++ -target x86_64-macos-none"
	python3 -m cibuildwheel --output-dir $(OUTPUT_DIR) --platform macos .

build-win:
	@echo "🪟 Building Windows (Docker/Cross) wheels..."
	docker run --rm -v "$(PWD):/io" quay.io/pypa/manylinux2014_x86_64 /io/scripts/build_win.sh

clean:
	rm -rf $(OUTPUT_DIR) build/ *.egg-info
