#!/usr/bin/env bash

PIDFILE=/tmp/dictation.pid
AUDIOFILE=/tmp/dictation.wav
RESULTFILE=/tmp/dictation_result.txt

# Create timestamp variable
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
# Create logs directory if it doesn't exist
mkdir -p logs
# Define log file with timestamp
LOGFILE="voice_agent/logs/dictation_${TIMESTAMP}.log"

# Get current clipboard content and escape it
CLIPBOARD_CONTENT=$(xclip -selection c -o)

# Command or script to perform transcription
# Using array to properly handle arguments with spaces
PYTHON_SCRIPT="/home/vamsi/voice_agent/process_speech.py"

# Function to log messages to both console and log file
log_message() {
    echo "$1" | tee -a "$LOGFILE"
}

if [ -f "$PIDFILE" ]; then
    # We are currently recording. Time to stop and transcribe.
    # log_message "Stopping recording..."
    REC_PID=$(cat "$PIDFILE")
    kill "$REC_PID" 2>/dev/null
    rm "$PIDFILE"

    # Transcribe the audio using proper argument handling
    # log_message "Transcribing..."
    python3 "$PYTHON_SCRIPT" "$AUDIOFILE" "$CLIPBOARD_CONTENT" > "$RESULTFILE" 2>/dev/null

    # Copy the result to clipboard
    cat "$RESULTFILE" | xclip -selection c

    # Get the active window class to determine if it's a terminal
    WINDOW_CLASS=$(xprop -id $(xdotool getactivewindow) WM_CLASS 2>/dev/null | grep -o '".*"' | tail -n 1 | sed 's/"//g')
    
    # For terminals, use xdotool type to directly type the content
    if [[ "$WINDOW_CLASS" =~ (terminal|konsole|xterm|rxvt|kitty|alacritty) ]]; then
        # Small delay to ensure window focus
        sleep 0.1
        # Read the result and type it directly
        xdotool type "$(cat $RESULTFILE)"
    else
        # For non-terminals, use normal paste
        xdotool key Ctrl+v
    fi
    
    # Copy transcription result to log file
    # log_message "Transcription result:"
    cat "$RESULTFILE" >> "$LOGFILE"

    # Clean up audio file if desired
    rm "$AUDIOFILE" "$RESULTFILE" 2>/dev/null
else
    # We are not recording. Start recording.
    # log_message "Starting recording..."
    # arecord: capture 16-bit, 44.1kHz, on default mic
    # Adjust settings (e.g., -D plughw:1,0) if you have a specific mic device
    arecord -f cd "$AUDIOFILE" &
    echo $! > "$PIDFILE"
fi 