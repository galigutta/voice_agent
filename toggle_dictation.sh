#!/usr/bin/env bash

# Set to 1 to enable debug logging, 0 to disable
DEBUG=0

PIDFILE=/tmp/dictation.pid
AUDIOFILE=/tmp/dictation.wav
RESULTFILE=/tmp/dictation_result.txt
RECORD_DEVICE=${VOICE_AGENT_RECORD_DEVICE:-pipewire}

# Create logs directory if needed (even if DEBUG=0, for potential error logs)
mkdir -p logs

# Only create timestamped log files when debugging is enabled
if [ $DEBUG -eq 1 ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    LOGFILE="voice_agent/logs/dictation_${TIMESTAMP}.log"
else
    # Use /dev/null when debug is disabled
    LOGFILE="/dev/null"
fi

# Get the appropriate Python command
GET_PYTHON_CMD="/home/vamsi/voice_agent/get_python_cmd.sh"
CLIENT_SCRIPT="/home/vamsi/voice_agent/whisper_client.py"

# Map typographic punctuation to ASCII so xdotool never has to remap a scratch keycode
asciify() {
    sed -e "s/[‘’ʼ]/'/g" -e 's/[“”]/"/g' -e 's/[–—]/-/g' -e 's/…/.../g' -e 's/\xC2\xA0/ /g'
}

# Function to log messages to both console and log file
log_message() {
    # Only log if debugging is enabled or it's an error message
    if [ $DEBUG -eq 1 ] || [[ "$1" == Error:* ]]; then
        echo "$1" | tee -a "$LOGFILE"
    fi
}

if [ -f "$PIDFILE" ]; then
    PYTHON_CMD=$($GET_PYTHON_CMD)
    if [ $? -ne 0 ]; then
        notify-send "Voice Agent Error" "No suitable Python environment found"
        exit 1
    fi

    # We are currently recording. Time to stop and transcribe.
    REC_PID=$(cat "$PIDFILE")
    kill "$REC_PID" 2>/dev/null
    rm "$PIDFILE"

    [ $DEBUG -eq 1 ] && log_message "Transcribing audio..."

    # Transcribe the audio, capturing both stdout and stderr
    RESULT=$("$PYTHON_CMD" "$CLIENT_SCRIPT" "$AUDIOFILE" 2>&1)
    EXIT_CODE=$?

    # Only log the result if debugging is enabled
    [ $DEBUG -eq 1 ] && echo "$RESULT" >> "$LOGFILE"

    # Check if the command failed
    if [ $EXIT_CODE -ne 0 ] || [[ "$RESULT" == Error:* ]]; then
        # Always log errors, even if DEBUG=0
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        ERROR_LOGFILE="voice_agent/logs/error_${TIMESTAMP}.log"
        echo "Error transcribing audio. See log for details." | tee -a "$ERROR_LOGFILE"
        echo "$RESULT" >> "$ERROR_LOGFILE"
        # Type the error message
        xdotool type --delay 1 "$(printf %s "$RESULT" | asciify)"
    else
        # Success - type the result directly
        xdotool type --delay 1 "$(printf %s "$RESULT" | asciify)"
    fi

    # Clean up audio file
    rm "$AUDIOFILE" 2>/dev/null
else
    # We are not recording. Start recording.
    [ $DEBUG -eq 1 ] && log_message "Starting recording..."
    # Use the PipeWire ALSA device (default source) so system audio settings choose the microphone.
    arecord -D "$RECORD_DEVICE" -f cd -r 44100 -q "$AUDIOFILE" &
    echo $! > "$PIDFILE"
fi
