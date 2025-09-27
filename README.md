# Voice Agent

A high-performance Linux voice dictation system using OpenAI's Whisper for speech-to-text and GPT-4 for intelligent context-aware processing. Features an optimized client-server architecture that keeps the Whisper model loaded in memory for instant transcription.

## Architecture

- **Whisper Server/Client**: Persistent server (`whisper_server.py`) keeps the Whisper model loaded, lightweight client (`whisper_client.py`) sends requests via Unix socket
- **Two Processing Modes**:
  - **Simple Mode** (`toggle_dictation.sh`): Direct transcription using Whisper only
  - **Terminal Command Mode** (`toggle_dictation_append.sh`): Voice-to-terminal command conversion with GPT-5
- **Auto-Recovery**: Client automatically starts server if needed, cleans up stale processes

## Features

- **Optimized Performance**: Server keeps Whisper model in memory (no reload delays)
- **Smart Transcription**: Uses OpenAI's Whisper "small.en" model for accurate speech-to-text
- **Voice-to-Command Processing**: GPT-5 converts speech to Ubuntu terminal commands (e.g., "list files" → `ls -la`)
- **Selected Text Context**: Uses selected text as context for smarter command generation
- **Automatic Pasting**: Results are automatically pasted into your active window
- **Robust Error Handling**: Includes logging, auto-recovery, and detailed troubleshooting guide

## Requirements

- Linux (tested on Ubuntu/Debian)
- Python 3.8+ with conda/miniconda
- OpenAI API key
- Working microphone

## Installation

1. **Install system dependencies**:
```bash
sudo apt-get install alsa-utils xclip xdotool xbindkeys psutil
```

2. **Install Python packages** (preferably in conda environment):
```bash
conda install openai-whisper pydantic openai python-dotenv psutil -y
# OR with pip:
pip install openai-whisper pydantic openai python-dotenv psutil
```

3. **Clone and configure**:
```bash
git clone https://github.com/yourusername/voice_agent.git
cd voice_agent
echo "OPENAI_API_KEY=your_key_here" > .env
chmod +x toggle_dictation.sh toggle_dictation_append.sh whisper_server.py whisper_client.py
```

4. **Set up keyboard shortcuts** (add to `~/.xbindkeysrc`):
```bash
"~/voice_agent/toggle_dictation.sh"
  Control + Alt + d

"~/voice_agent/toggle_dictation_append.sh"
  Control + Alt + a
```

Then reload: `xbindkeys --poll-rc`

## Usage

### Simple Transcription (Ctrl+Alt+D)
1. Press hotkey to start recording
2. Speak clearly
3. Press hotkey again to stop and transcribe
4. Text is automatically pasted

### Terminal Command Mode (Ctrl+Alt+A)
1. Press hotkey to start recording
2. Speak your terminal command request
3. Press hotkey again to stop
4. GPT-5 converts speech to Ubuntu terminal command
5. Command is automatically pasted

### Examples
- **Simple Mode**: Natural dictation with automatic cleanup of filler words
- **Terminal Command Mode**: Say "list all files" → pastes `ls -la`, or "install docker" → pastes `sudo apt-get install docker.io`
- **With Selected Text**: Select "myfile.txt", say "delete this" → pastes `rm myfile.txt`

## How It Works

1. **Recording**: Uses `arecord` to capture audio from microphone
2. **Server Management**: Client checks/starts Whisper server as needed
3. **Transcription**: Audio sent to server via Unix socket for processing
4. **Command Generation** (terminal mode only): Transcribed text converted to terminal commands by GPT-5
5. **Output**: Result copied to clipboard and auto-pasted with `xdotool`

## File Structure

- `whisper_server.py` - Persistent server that loads and manages Whisper model
- `whisper_client.py` - Lightweight client that communicates with server
- `process_with_gpt.py` - GPT-5 processing for voice-to-terminal command conversion
- `toggle_dictation.sh` - Simple transcription mode script
- `toggle_dictation_append.sh` - Terminal command mode script
- `TROUBLESHOOTING.md` - Detailed troubleshooting guide

## Logs & Debugging

- Server logs: `/tmp/whisper_server.log`
- Dictation logs: `logs/dictation_[timestamp].log` (when DEBUG=1 in scripts)
- Server PID: `/tmp/whisper_server.pid`
- Unix socket: `/tmp/whisper_server.sock`

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions to common issues including:
- Connection refused errors
- Server startup failures
- API key issues
- System resource constraints

Quick fixes:
```bash
# Check if server is running
ps aux | grep whisper_server

# View server logs
tail -f /tmp/whisper_server.log

# Full reset
pkill -f whisper_server.py
rm -f /tmp/whisper_server.* /tmp/dictation.*
```

## License
[Your chosen license] 