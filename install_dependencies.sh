#!/usr/bin/env bash

echo "Installing required dependencies for Whisper Voice Agent"

# Get the path to the current conda environment's Python
CONDA_PYTHON=$(which python)

if [[ $CONDA_PYTHON == *"/miniconda3/"* ]] || [[ $CONDA_PYTHON == *"/anaconda3/"* ]]; then
  echo "Using conda environment: $CONDA_PYTHON"
else
  echo "Error: Not running in a conda environment."
  echo "Please activate your conda environment first:"
  echo "  source ~/miniconda3/bin/activate"
  echo "  conda activate base  # or your env name"
  exit 1
fi

# Install conda packages
echo "Installing conda packages..."
conda install -y \
  pydantic \
  || { echo "Warning: Some conda packages failed to install"; }

# Install pip packages
echo "Installing pip packages..."
pip install --no-input \
  openai-whisper \
  openai \
  python-dotenv \
  pydantic \
  || { echo "Error: Failed to install pip packages"; exit 1; }

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