#!/usr/bin/env bash

# Set to 1 to enable debug logging, 0 to disable
DEBUG=0

PIDFILE=/tmp/dictation.pid
AUDIOFILE=/tmp/dictation.wav
RESULTFILE=/tmp/dictation_result.txt

# Create logs directory if needed
mkdir -p logs

# Only create timestamped log files when debugging is enabled
if [ $DEBUG -eq 1 ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    LOGFILE="logs/dictation_append_${TIMESTAMP}.log"
else
    LOGFILE="/dev/null"
fi

# Use the whisper client for transcription (same as toggle_dictation.sh)
TRANSCRIBE_CMD="/home/vamsi/miniconda3/bin/python /home/vamsi/voice_agent/whisper_client.py $AUDIOFILE"

# GPT processing script
GPT_SCRIPT="/home/vamsi/voice_agent/process_with_gpt.py"

# Function to log messages
log_message() {
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

    # First, transcribe the audio using whisper_client
    TRANSCRIBED=$($TRANSCRIBE_CMD 2>&1)
    TRANSCRIBE_EXIT_CODE=$?

    if [ $TRANSCRIBE_EXIT_CODE -ne 0 ] || [[ "$TRANSCRIBED" == Error:* ]]; then
        # Transcription failed
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        ERROR_LOGFILE="logs/error_${TIMESTAMP}.log"
        echo "Error transcribing audio. See log for details." | tee -a "$ERROR_LOGFILE"
        echo "$TRANSCRIBED" >> "$ERROR_LOGFILE"
        # Type the error message
        xdotool type --delay 1 "$TRANSCRIBED"
    else
        # Transcription succeeded, now process with GPT to convert to terminal command
        [ $DEBUG -eq 1 ] && log_message "Transcribed: $TRANSCRIBED"

        # Capture the currently selected text (if any) for context
        SELECTED_TEXT=$(xclip -selection primary -o 2>/dev/null)

        [ $DEBUG -eq 1 ] && [ -n "$SELECTED_TEXT" ] && log_message "Selected text: $SELECTED_TEXT"
        [ $DEBUG -eq 1 ] && log_message "Converting to terminal command..."

        # Process with GPT to convert to terminal command, passing selected text if available
        if [ -n "$SELECTED_TEXT" ]; then
            RESULT=$(/home/vamsi/miniconda3/bin/python "$GPT_SCRIPT" "$TRANSCRIBED" "$SELECTED_TEXT" 2>&1)
        else
            RESULT=$(/home/vamsi/miniconda3/bin/python "$GPT_SCRIPT" "$TRANSCRIBED" 2>&1)
        fi

        GPT_EXIT_CODE=$?

        if [ $GPT_EXIT_CODE -ne 0 ]; then
            # GPT processing failed, use original transcription
            [ $DEBUG -eq 1 ] && log_message "GPT processing failed, using original transcription"
            RESULT="$TRANSCRIBED"
        fi

        [ $DEBUG -eq 1 ] && log_message "Final result: $RESULT"

        # Type the result directly
        xdotool type --delay 1 "$RESULT"
    fi
    
    # Clean up audio file
    rm "$AUDIOFILE" 2>/dev/null
else
    # We are not recording. Start recording.
    [ $DEBUG -eq 1 ] && log_message "Starting recording..."
    # Using same recording settings as toggle_dictation.sh
    arecord -f cd -r 44100 -q "$AUDIOFILE" &
    echo $! > "$PIDFILE"
fi