#!/usr/bin/env python3
import os
import sys
import json
import socket
import signal

# Check for required packages
required_packages = {
    "whisper": "openai-whisper",
    "pydantic": "pydantic",
    "openai": "openai",
    "dotenv": "python-dotenv"
}

missing_packages = []
for module, package in required_packages.items():
    try:
        __import__(module)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    print(f"Error: Missing required packages: {', '.join(missing_packages)}")
    print("Please install them using:")
    print(f"conda install {' '.join(missing_packages)}")
    sys.exit(1)

# Now that we've checked dependencies, import them
import whisper
from pydantic import BaseModel
from openai import OpenAI
import dotenv

# Load environment variables
dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Server configuration
SERVER_SOCKET = '/tmp/whisper_server.sock'
PID_FILE = '/tmp/whisper_server.pid'

# Pydantic model for cleaned text
class CleanedText(BaseModel):
    thoughts: str
    response: str

# Load the whisper model once at startup (this is the key optimization)
print("Loading whisper model 'small.en'...")
model = whisper.load_model("small.en")
print("Model loaded and ready!")

# Write PID file for easy cleanup later
with open(PID_FILE, 'w') as f:
    f.write(str(os.getpid()))

def clean_text(text):
    completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Clean up any filler words, punctuation, and other noise from the text."},
        {"role": "user", "content": text},
    ],
    response_format=CleanedText)
    return completion.choices[0].message.parsed

def get_command(text):
    completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that can help me with my tasks. I will give you some context and a command. respond appropriately. If there is a linux shell prompt in the context, respond with the command to execute the request and nothing else. not even the ~."},
        {"role": "user", "content": text},
    ],
    response_format=CleanedText)
    return completion.choices[0].message.parsed

def transcribe_audio(audio_file, clipboard_content=None):
    """Transcribe audio file using the pre-loaded whisper model"""
    try:
        result = model.transcribe(audio_file)
        text = result["text"].strip()
        
        if clipboard_content:
            param = f"<context>{clipboard_content}</context> <command>{text}</command>"
            response = get_command(param)
            return response.response
        else:
            return text
    except Exception as e:
        return f"Error transcribing: {str(e)}"

def handle_client(client_socket):
    """Handle client connection and transcription request"""
    try:
        # Receive the request
        data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            # Check if we have a complete message
            if data.endswith(b'\n\n'):
                break
                
        request = json.loads(data.decode('utf-8').strip())
        audio_file = request.get('audio_file')
        clipboard_content = request.get('clipboard_content')
        
        # Process the transcription
        result = transcribe_audio(audio_file, clipboard_content)
        
        # Send the response
        client_socket.sendall(json.dumps({'result': result}).encode('utf-8'))
    except Exception as e:
        client_socket.sendall(json.dumps({'error': str(e)}).encode('utf-8'))
    finally:
        client_socket.close()

def main():
    """Main server loop"""
    # Remove socket if it already exists
    if os.path.exists(SERVER_SOCKET):
        os.unlink(SERVER_SOCKET)
        
    # Create a socket
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SERVER_SOCKET)
    server.listen(5)
    
    # Set up signal handlers for graceful shutdown
    def handle_signal(sig, frame):
        print("Shutting down...")
        server.close()
        if os.path.exists(SERVER_SOCKET):
            os.unlink(SERVER_SOCKET)
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    print(f"Server started at {SERVER_SOCKET}")
    
    # Server loop
    while True:
        client_socket, _ = server.accept()
        handle_client(client_socket)

if __name__ == "__main__":
    main() 