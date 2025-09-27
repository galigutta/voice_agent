#!/usr/bin/env bash

# Find the appropriate Python environment with whisper installed
# Priority: uv venv > conda > system python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for uv virtual environment (preferred)
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    echo "$SCRIPT_DIR/.venv/bin/python"
    exit 0
fi

# Check for conda environments
for conda_path in "$HOME/miniconda3" "$HOME/anaconda3" "$CONDA_PREFIX"; do
    if [ -n "$conda_path" ] && [ -f "$conda_path/bin/python" ]; then
        if "$conda_path/bin/python" -c "import whisper" 2>/dev/null; then
            echo "$conda_path/bin/python"
            exit 0
        fi
    fi
done

# Fallback to system python3
if command -v python3 &> /dev/null && python3 -c "import whisper" 2>/dev/null; then
    echo "python3"
    exit 0
fi

echo "Error: No Python environment with whisper found" >&2
exit 1