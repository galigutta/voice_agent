#!/usr/bin/env python3
import sys
import json
import socket
import subprocess
import os
import time
import psutil

# Server socket path
SERVER_SOCKET = '/tmp/whisper_server.sock'
SERVER_PID_FILE = '/tmp/whisper_server.pid'
SERVER_LOG_FILE = '/tmp/whisper_server.log'

def is_server_running():
    """Check if the server process is actually running"""
    if not os.path.exists(SERVER_PID_FILE):
        return False
    
    try:
        with open(SERVER_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process with this PID exists and is our server
        if psutil.pid_exists(pid):
            proc = psutil.Process(pid)
            # Check if it's actually our whisper server
            if 'whisper_server.py' in ' '.join(proc.cmdline()):
                return True
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    
    return False

def cleanup_stale_files():
    """Clean up stale server files if server is not running"""
    if not is_server_running():
        for file_path in [SERVER_SOCKET, SERVER_PID_FILE]:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"Cleaned up stale file: {file_path}")
                except OSError:
                    pass

def start_server_if_needed():
    """Start the whisper server if it's not already running"""
    # First, clean up any stale files
    cleanup_stale_files()
    
    if not os.path.exists(SERVER_SOCKET) or not is_server_running():
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
            if os.path.exists(SERVER_SOCKET) and is_server_running():
                print("Server started successfully")
                return
            
            # After a few seconds, check if there were startup errors
            if i == 5:
                try:
                    with open(SERVER_LOG_FILE, 'r') as f:
                        log_content = f.read()
                        if "Error:" in log_content:
                            print("Server failed to start:")
                            # Print last few lines of log
                            lines = log_content.strip().split('\n')
                            for line in lines[-10:]:
                                if line.strip():
                                    print(line)
                            print(f"\nFull log available at: {SERVER_LOG_FILE}")
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
    max_retries = 2
    
    for attempt in range(max_retries):
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
            client.settimeout(30)  # 30 second timeout
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
            result = response.get('result', response.get('error', 'Unknown error'))
            
            # If we got here, the request was successful
            return result
            
        except (ConnectionRefusedError, FileNotFoundError, socket.timeout) as e:
            if attempt < max_retries - 1:
                print(f"Connection failed (attempt {attempt + 1}), cleaning up and retrying...")
                cleanup_stale_files()
                time.sleep(2)
                continue
            else:
                return f"Error: Failed to connect to server after {max_retries} attempts: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            try:
                client.close()
            except:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: whisper_client.py <audio.wav> [clipboard_content]")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    clipboard_content = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = send_transcription_request(audio_file, clipboard_content)
    print(result) 