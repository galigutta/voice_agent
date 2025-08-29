#!/bin/bash

echo "Testing voice-to-command conversion..."
echo "======================================"

# Test various voice commands
test_commands=(
    "list all files"
    "show current directory"
    "create a folder called test"
    "search for python files"
    "check disk usage"
    "show running processes"
    "what's my IP address"
    "copy readme to backup"
)

for cmd in "${test_commands[@]}"; do
    echo -e "\nVoice input: \"$cmd\""
    result=$(/home/vamsi/miniconda3/bin/python /home/vamsi/voice_agent/process_with_gpt.py "$cmd" 2>&1)
    if [ $? -eq 0 ]; then
        echo "Terminal command: $result"
    else
        echo "Error: $result"
    fi
done

echo -e "\n======================================"
echo "Test complete!"