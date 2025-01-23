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

# Command or script to perform transcription
# (Update the path to your Python transcription script below)
TRANSCRIBE_CMD="python3 /home/vamsi/voice_agent/process_speech.py $AUDIOFILE"

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

    # Transcribe the audio
    # log_message "Transcribing..."
    $TRANSCRIBE_CMD > "$RESULTFILE" 2>/dev/null

    # Put the result on the clipboard
    cat "$RESULTFILE" | xclip -selection c

    # Optionally paste it automatically into the active window:
    xdotool key Ctrl+v
    
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
