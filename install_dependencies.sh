#!/usr/bin/env bash

echo "Installing required dependencies for Whisper Voice Agent"

# Check if uv is available
if ! command -v uv &> /dev/null; then
  echo "Error: uv is not installed."
  echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "Using uv for package management"

# Check for required system dependencies
MISSING_DEPS=()

if ! command -v ffmpeg &> /dev/null; then
  MISSING_DEPS+=("ffmpeg")
fi

if ! command -v xdotool &> /dev/null; then
  MISSING_DEPS+=("xdotool")
fi

if ! command -v arecord &> /dev/null; then
  MISSING_DEPS+=("alsa-utils")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
  echo ""
  echo "Missing system dependencies: ${MISSING_DEPS[*]}"
  echo ""
  read -p "Install them with sudo? [Y/n] " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    sudo apt install -y "${MISSING_DEPS[@]}" || { echo "Error: Failed to install system dependencies"; exit 1; }
  else
    echo "Please install manually: sudo apt install ${MISSING_DEPS[*]}"
    exit 1
  fi
fi

# Install packages with uv
echo "Installing Python packages..."
uv pip install \
  openai-whisper \
  openai \
  python-dotenv \
  pydantic \
  || { echo "Error: Failed to install packages"; exit 1; }

# Make scripts executable
chmod +x whisper_server.py whisper_client.py toggle_dictation.sh

echo "All dependencies installed successfully!"
echo ""
echo "To use the voice agent:"
echo "1. First start the server: ./whisper_server.py"
echo "   (or it will start automatically when needed)"
echo ""
echo "2. Run the toggle_dictation.sh script to start/stop recording:"
echo "   ./toggle_dictation.sh"
echo ""
echo "You may want to bind toggle_dictation.sh to a keyboard shortcut for convenience." 