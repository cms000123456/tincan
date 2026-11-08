#!/usr/bin/env bash
# Tin Can Chronicles launcher (Linux)
set -e
cd "$(dirname "$0")"

PY=python3
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    # create a local venv with pygame if none exists
    if ! $PY -c "import pygame" 2>/dev/null; then
        echo "* creating virtual environment..."
        $PY -m venv .venv
        ./.venv/bin/pip install --quiet pygame
        PY=".venv/bin/python"
    fi
fi

exec $PY main.py "$@"
