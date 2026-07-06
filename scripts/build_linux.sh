#!/bin/bash
set -e
# Use a specific python version installed in the container
PYTHON_BIN=/opt/python/cp312-cp312/bin/python

# Navigate to the repo root
cd /io

# Set a writable HOME directory for the non-root user
export HOME=/tmp/build_home
mkdir -p $HOME

# Ensure the 'build' package is available for this python version
$PYTHON_BIN -m pip install --user build

# Build the wheel for ice-engine. 
# 'build' will create its own isolated environment for dependencies.
$PYTHON_BIN -m build . --wheel --outdir /io/dist/linux
