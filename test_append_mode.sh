#!/bin/bash

echo "Testing toggle_dictation_append.sh components..."
echo "================================================"

# Test 1: Check if whisper_client works
echo -e "\n1. Testing whisper_client.py:"
echo "test" > /tmp/test_audio.wav
RESULT=$(/home/vamsi/miniconda3/bin/python /home/vamsi/voice_agent/whisper_client.py /tmp/test_audio.wav 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ Whisper client works"
else
    echo "✗ Whisper client failed: $RESULT"
fi

# Test 2: Check if GPT processing works
echo -e "\n2. Testing GPT processing:"
TEST_TEXT="list all files"
TEST_CONTEXT="user@host:~$"
RESULT=$(/home/vamsi/miniconda3/bin/python /home/vamsi/voice_agent/process_with_gpt.py "$TEST_TEXT" "$TEST_CONTEXT" 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ GPT processing works"
    echo "   Input: '$TEST_TEXT' with context '$TEST_CONTEXT'"
    echo "   Output: '$RESULT'"
else
    echo "✗ GPT processing failed: $RESULT"
fi

# Test 3: Check OpenAI API key
echo -e "\n3. Checking OpenAI API key:"
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OPENAI_API_KEY is set in environment"
else
    # Check .env file
    if [ -f "/home/vamsi/voice_agent/.env" ]; then
        if grep -q "OPENAI_API_KEY" "/home/vamsi/voice_agent/.env"; then
            echo "✓ OPENAI_API_KEY found in .env file"
        else
            echo "✗ OPENAI_API_KEY not found in .env file"
        fi
    else
        echo "✗ No .env file found and OPENAI_API_KEY not in environment"
    fi
fi

# Test 4: Check if recording works
echo -e "\n4. Testing audio recording:"
echo "Recording 2 seconds of audio..."
arecord -f cd -r 44100 -d 2 /tmp/test_record.wav 2>/dev/null
if [ -f "/tmp/test_record.wav" ] && [ -s "/tmp/test_record.wav" ]; then
    echo "✓ Audio recording works"
    rm /tmp/test_record.wav
else
    echo "✗ Audio recording failed"
fi

# Test 5: Enable debug mode for next run
echo -e "\n5. Enabling debug mode for next run:"
sed -i 's/DEBUG=0/DEBUG=1/' /home/vamsi/voice_agent/toggle_dictation_append.sh
echo "✓ Debug mode enabled. Check logs/dictation_append_*.log after next use"

echo -e "\n================================================"
echo "Diagnostics complete. Try using Ctrl+Menu now."
echo "If it fails, check the log file in logs/ directory"