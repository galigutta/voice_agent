#!/usr/bin/env bash

# Find the appropriate Python environment with whisper installed
# Priority: uv venv > conda > system python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="$HOME/.cache/voice_agent"
CACHE_FILE="$CACHE_DIR/python_cmd"

print_and_cache() {
    local cmd="$1"
    mkdir -p "$CACHE_DIR"
    printf '%s\n' "$cmd" > "$CACHE_FILE"
    echo "$cmd"
    exit 0
}

# Allow manual override
if [ -n "$VOICE_AGENT_PYTHON" ] && command -v "$VOICE_AGENT_PYTHON" >/dev/null 2>&1; then
    print_and_cache "$VOICE_AGENT_PYTHON"
fi

# Use cached interpreter if available and still valid
if [ -f "$CACHE_FILE" ]; then
    if read -r CACHED_CMD < "$CACHE_FILE"; then
        if [ -n "$CACHED_CMD" ] && command -v "$CACHED_CMD" >/dev/null 2>&1; then
            echo "$CACHED_CMD"
            exit 0
        else
            rm -f "$CACHE_FILE"
        fi
    fi
fi

# Check for uv virtual environment (preferred)
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    print_and_cache "$SCRIPT_DIR/.venv/bin/python"
fi

# Check for conda environments
for conda_path in "$HOME/miniconda3" "$HOME/anaconda3" "$CONDA_PREFIX"; do
    if [ -n "$conda_path" ] && [ -f "$conda_path/bin/python" ]; then
        if "$conda_path/bin/python" -c "import whisper" 2>/dev/null; then
            print_and_cache "$conda_path/bin/python"
        fi
    fi
done

# Fallback to system python3
if command -v python3 >/dev/null 2>&1 && python3 -c "import whisper" 2>/dev/null; then
    print_and_cache "python3"
fi

echo "Error: No Python environment with whisper found" >&2
exit 1
