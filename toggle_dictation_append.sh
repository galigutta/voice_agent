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
        echo "$TRANSCRIBED" | xclip -selection c
    else
        # Transcription succeeded, now process with GPT to convert to terminal command
        [ $DEBUG -eq 1 ] && log_message "Transcribed: $TRANSCRIBED"
        [ $DEBUG -eq 1 ] && log_message "Converting to terminal command..."
        
        # Process with GPT to convert to terminal command (no clipboard needed)
        RESULT=$(/home/vamsi/miniconda3/bin/python "$GPT_SCRIPT" "$TRANSCRIBED" 2>&1)
        
        GPT_EXIT_CODE=$?
        
        if [ $GPT_EXIT_CODE -ne 0 ]; then
            # GPT processing failed, use original transcription
            [ $DEBUG -eq 1 ] && log_message "GPT processing failed, using original transcription"
            RESULT="$TRANSCRIBED"
        fi
        
        [ $DEBUG -eq 1 ] && log_message "Final result: $RESULT"
        
        # Copy result to clipboard
        echo "$RESULT" | xclip -selection c
    fi
    
    # Get the active window class to determine if it's a terminal
    WINDOW_CLASS=$(xprop -id $(xdotool getactivewindow) WM_CLASS 2>/dev/null | grep -o '"[^"]*"' | tr '[:upper:]' '[:lower:]')
    
    # Check if it's a terminal window or VSCode (case-insensitive match)
    if echo "$WINDOW_CLASS" | grep -qiE '(terminal|konsole|xterm|rxvt|kitty|alacritty|gnome-terminal|terminator|tilix|urxvt|st-256color|wezterm|foot|code|vscode|codium|code-oss|termius)'; then
        # For terminals, use Ctrl+Shift+v
        xdotool key Ctrl+Shift+v
    else
        # For non-terminals, use normal paste
        xdotool key Ctrl+v
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