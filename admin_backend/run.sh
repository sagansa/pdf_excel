#!/bin/bash
# Convenience script to run the Flask server using the project's virtual environment.
# Usage: ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Error: virtual environment not found at ./venv"
    echo "Create it with: /opt/homebrew/bin/python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Activate the venv so 'python' resolves to the venv's interpreter
source venv/bin/activate
python server.py