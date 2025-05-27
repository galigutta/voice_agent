# Voice Agent Troubleshooting Guide

## "Connection Refused" Error

### Symptoms
- Error message: `[Errno 111] Connection refused`
- Voice dictation stops working
- Server appears to be running but client can't connect

### Root Cause
The whisper server process dies/crashes after startup, leaving behind stale files (`/tmp/whisper_server.sock`, `/tmp/whisper_server.pid`) but no running process. When the client tries to connect, it gets "Connection refused" because there's no server listening.

### Common Causes After System Updates

1. **Missing/Invalid OpenAI API Key**
   - Server crashes when trying to make API calls
   - Check: `echo $OPENAI_API_KEY` (should show your API key)
   - Fix: Set the environment variable in your shell profile

2. **Python Package Compatibility Issues**
   - System updates may have updated Python packages
   - PyTorch, OpenAI, or Whisper library changes
   - Check: Look at `/tmp/whisper_server.log` for import errors

3. **Memory/Resource Constraints**
   - Whisper model loading requires significant memory
   - System updates might have changed memory management
   - Check: `free -h` to see available memory

4. **Network/Firewall Changes**
   - System updates might block OpenAI API access
   - Check: Try making a test API call manually

### Diagnostic Steps

1. **Check if server is actually running:**
   ```bash
   ps aux | grep whisper_server
   cat /tmp/whisper_server.pid
   ps -p $(cat /tmp/whisper_server.pid)
   ```

2. **Check server logs:**
   ```bash
   cat /tmp/whisper_server.log
   tail -f /tmp/whisper_server.log  # Watch in real-time
   ```

3. **Test manual server startup:**
   ```bash
   cd /home/vamsi/voice_agent
   python whisper_server.py
   ```

4. **Check system resources:**
   ```bash
   free -h
   df -h /tmp
   ```

### Quick Fixes

1. **Restart the server:**
   ```bash
   pkill -f whisper_server.py
   rm -f /tmp/whisper_server.*
   python whisper_server.py &
   ```

2. **Clean up stale files:**
   ```bash
   rm -f /tmp/whisper_server.sock /tmp/whisper_server.pid
   ```

3. **Check environment variables:**
   ```bash
   source ~/.bashrc  # or ~/.zshrc
   echo $OPENAI_API_KEY
   ```

### Improvements Made

The code has been enhanced with:

1. **Better Error Handling:**
   - Comprehensive logging to `/tmp/whisper_server.log`
   - API key validation at startup
   - Graceful error recovery

2. **Stale File Detection:**
   - Client now checks if server process is actually running
   - Automatic cleanup of stale socket/PID files
   - Retry logic with proper cleanup

3. **Enhanced Diagnostics:**
   - Detailed error messages
   - Process validation using `psutil`
   - Connection timeout handling

### Prevention

1. **Monitor server logs regularly:**
   ```bash
   tail -f /tmp/whisper_server.log
   ```

2. **Set up proper environment:**
   - Ensure `OPENAI_API_KEY` is set in shell profile
   - Keep Python packages updated consistently

3. **Use the improved client:**
   - The updated `whisper_client.py` handles server restarts automatically
   - Includes retry logic and better error reporting

### Emergency Recovery

If nothing else works:

1. **Full reset:**
   ```bash
   pkill -f whisper_server.py
   rm -f /tmp/whisper_server.*
   rm -f /tmp/dictation.*
   ```

2. **Reinstall dependencies:**
   ```bash
   conda install openai-whisper pydantic openai python-dotenv psutil -y
   ```

3. **Test basic functionality:**
   ```bash
   echo "test" > /tmp/test.wav
   python whisper_client.py /tmp/test.wav
   ``` 