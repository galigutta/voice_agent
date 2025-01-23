# Voice Agent

A Linux voice dictation tool that uses OpenAI's Whisper for transcription and GPT for context-aware processing. It intelligently processes your voice input based on your current window context (terminal, editor, etc.) and clipboard content.

## Features
- Voice-to-text with context awareness (e.g., converts "list files" to `ls -la` in terminals)
- Two modes: Replace (`toggle_dictation.sh`) and Append (`toggle_dictation_append.sh`)
- Automatic clipboard handling and intelligent pasting
- Works in any application, with special handling for terminals

## Setup
1. Install dependencies:
```bash
sudo apt-get install alsa-utils xclip xdotool python3-pip xbindkeys
pip3 install openai whisper pydantic python-dotenv
```

2. Configure:
```bash
git clone https://github.com/yourusername/voice_agent.git
cd voice_agent
echo "OPENAI_API_KEY=your_key_here" > .env
chmod +x toggle_dictation.sh toggle_dictation_append.sh process_speech.py
```

3. Set keyboard shortcuts (using xbindkeys):
```bash
# Add to ~/.xbindkeysrc
"~/voice_agent/toggle_dictation.sh"
  Control + Alt + d

"~/voice_agent/toggle_dictation_append.sh"
  Control + Alt + a

xbindkeys --poll-rc  # Reload configuration
```

## Usage
1. Start recording: Use keyboard shortcut or run script directly
2. Speak your command/text
3. Use shortcut again or run script to stop and process
4. The tool will transcribe, process with context, and paste the result

## Troubleshooting
Check: microphone (`arecord -l`), clipboard (`xclip -version`), window detection (`xprop`)

## License
[Your chosen license] 