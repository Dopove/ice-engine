.PHONY: build-linux

OUTPUT_DIR := dist

build-linux:
	@echo "🐧 Building Linux Python wheels..."
	rm -rf $(OUTPUT_DIR) && mkdir -p $(OUTPUT_DIR)
	python3 -m cibuildwheel --output-dir $(OUTPUT_DIR) .
