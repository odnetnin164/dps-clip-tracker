#!/bin/bash

# Build script for Linux/macOS

set -e

echo "Setting up Python virtual environment..."
python -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running tests..."
python -m pytest tests/ -v

echo "Building executable..."
python build_spec.py

echo "Build completed! Executable can be found in dist/"