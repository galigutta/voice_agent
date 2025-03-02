#!/usr/bin/env python3
import sys
import json
import socket
import subprocess
import os
import time

# Server socket path
SERVER_SOCKET = '/tmp/whisper_server.sock'
SERVER_PID_FILE = '/tmp/whisper_server.pid'
SERVER_LOG_FILE = '/tmp/whisper_server.log'

def start_server_if_needed():
    """Start the whisper server if it's not already running"""
    if not os.path.exists(SERVER_SOCKET) or not os.path.exists(SERVER_PID_FILE):
        print("Starting whisper server...")
        server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whisper_server.py')
        
        # Make server script executable if it isn't already
        if not os.access(server_script, os.X_OK):
            os.chmod(server_script, 0o755)
            
        # Start the server with explicit python path from conda
        subprocess.Popen([sys.executable, server_script], 
                        stdout=open(SERVER_LOG_FILE, 'a'),
                        stderr=subprocess.STDOUT)
        
        # Wait for server to start
        for i in range(30):  # wait up to 30 seconds
            if os.path.exists(SERVER_SOCKET):
                print("Server started successfully")
                return
            
            # After a few seconds, check if there were startup errors
            if i == 5:
                try:
                    with open(SERVER_LOG_FILE, 'r') as f:
                        log_content = f.read()
                        if "Error: Missing required packages" in log_content:
                            print("Server failed to start due to missing packages:")
                            print(log_content)
                            print("\nCheck the server log for details: " + SERVER_LOG_FILE)
                            sys.exit(1)
                except:
                    pass
                    
            time.sleep(1)
            print(".", end="", flush=True)
            
        print("\nError: Server didn't start in time")
        print("Check the server log for details: " + SERVER_LOG_FILE)
        try:
            with open(SERVER_LOG_FILE, 'r') as f:
                print("\nLast 10 lines of server log:")
                lines = f.readlines()
                for line in lines[-10:]:
                    print(line.strip())
        except:
            pass
        sys.exit(1)

def send_transcription_request(audio_file, clipboard_content=None):
    """Send a transcription request to the whisper server"""
    try:
        # Make sure server is running
        start_server_if_needed()
        
        # Prepare request
        request = {
            'audio_file': audio_file,
        }
        if clipboard_content:
            request['clipboard_content'] = clipboard_content
        
        # Connect to server
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SERVER_SOCKET)
        
        # Send request
        client.sendall(json.dumps(request).encode('utf-8') + b'\n\n')
        
        # Get response
        data = b''
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
            
        response = json.loads(data.decode('utf-8'))
        return response.get('result', response.get('error', 'Unknown error'))
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: whisper_client.py <audio.wav> [clipboard_content]")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    clipboard_content = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = send_transcription_request(audio_file, clipboard_content)
    print(result) 