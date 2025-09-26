#!/usr/bin/env bash

# Set to 1 to enable debug logging, 0 to disable
DEBUG=0

PIDFILE=/tmp/dictation.pid
AUDIOFILE=/tmp/dictation.wav
RESULTFILE=/tmp/dictation_result.txt

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

# Use the client script with absolute path instead of tilde expansion
TRANSCRIBE_CMD="/home/vamsi/miniconda3/bin/python /home/vamsi/voice_agent/whisper_client.py $AUDIOFILE"

# Function to log messages to both console and log file
log_message() {
    # Only log if debugging is enabled or it's an error message
    if [ $DEBUG -eq 1 ] || [[ "$1" == Error:* ]]; then
        echo "$1" | tee -a "$LOGFILE"
    fi
}

if [ -f "$PIDFILE" ]; then
    # We are currently recording. Time to stop and transcribe.
    REC_PID=$(cat "$PIDFILE")
    kill "$REC_PID" 2>/dev/null
    rm "$PIDFILE"

    [ $DEBUG -eq 1 ] && log_message "Transcribing audio..."
    
    # Transcribe the audio, capturing both stdout and stderr
    RESULT=$($TRANSCRIBE_CMD 2>&1)
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
        xdotool type --delay 1 "$RESULT"
    else
        # Success - type the result directly
        xdotool type --delay 1 "$RESULT"
    fi
    
    # Clean up audio file
    rm "$AUDIOFILE" 2>/dev/null
else
    # We are not recording. Start recording.
    [ $DEBUG -eq 1 ] && log_message "Starting recording..."
    # Using higher quality settings might improve transcription
    arecord -f cd -r 44100 -q "$AUDIOFILE" &
    echo $! > "$PIDFILE"
fi
