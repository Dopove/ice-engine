#!/bin/bash
set -e
# Use a specific python version installed in the container
PYTHON_BIN=/opt/python/cp312-cp312/bin/python

# Navigate to the repo root
cd /io

# Install dependency and build using the minimal requirements
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -r requirements.minimal.txt
$PYTHON_BIN -m build . --wheel --outdir /io/dist
EOF
chmod +x scripts/build_linux.sh
