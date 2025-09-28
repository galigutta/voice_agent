#!/usr/bin/env python3
import os
import sys
import json
import socket
import signal
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/tmp/whisper_server.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Check for required packages
required_packages = {
    "whisper": "openai-whisper",
    "pydantic": "pydantic",
    "openai": "openai",
    "dotenv": "python-dotenv",
    "psutil": "psutil",
}

missing_packages = []
for module, package in required_packages.items():
    try:
        __import__(module)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    error_msg = f"Error: Missing required packages: {', '.join(missing_packages)}"
    logger.error(error_msg)
    print(error_msg)
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

# Validate OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set")
    print("Error: OPENAI_API_KEY environment variable is not set")
    sys.exit(1)

try:
    client = OpenAI(api_key=api_key)
    # Test the API key with a minimal request
    logger.info("Testing OpenAI API connection...")
    test_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=1,
    )
    logger.info("OpenAI API connection successful")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    print(f"Error: Failed to initialize OpenAI client: {e}")
    sys.exit(1)

# Server configuration
SERVER_SOCKET = "/tmp/whisper_server.sock"
PID_FILE = "/tmp/whisper_server.pid"


# Pydantic model for cleaned text
class CleanedText(BaseModel):
    thoughts: str
    response: str


# Check CUDA availability and fail fast if corrupted
import torch
if torch.cuda.is_available():
    try:
        # Test CUDA functionality
        test_tensor = torch.zeros(1).cuda()
        logger.info(f"CUDA is available. Using GPU: {torch.cuda.get_device_name()}")
        device = "cuda"
    except Exception as e:
        logger.error(f"CUDA is available but not functional: {e}")
        logger.error("CUDA context appears corrupted. Please restart the server with GPU reset.")
        sys.exit(1)
else:
    logger.warning("CUDA not available. Using CPU (this will be slower)")
    device = "cpu"

# Load the whisper model once at startup (this is the key optimization)
print(f"Loading whisper model 'small.en' on {device}...")
model = whisper.load_model("small.en", device=device)
current_device = device
print("Model loaded and ready!")

# Function to reload model on different device
def reload_model_on_device(target_device):
    """Reload whisper model on specified device"""
    global model, current_device
    try:
        logger.info(f"Reloading model on {target_device} device")
        model = whisper.load_model("small.en", device=target_device)
        current_device = target_device
        logger.info(f"Model successfully reloaded on {target_device}")
        return True
    except Exception as e:
        logger.error(f"Failed to reload model on {target_device}: {e}")
        return False

# Write PID file for easy cleanup later
with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))


def clean_text(text):
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Clean up any filler words, punctuation, and other noise from the text.",
                },
                {"role": "user", "content": text},
            ],
            response_format=CleanedText,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error in clean_text: {e}")
        raise


def get_command(text):
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that can help me with my tasks. I will give you some context and a command. respond appropriately. If there is a linux shell prompt in the context, respond with the command to execute the request and nothing else. not even the ~.",
                },
                {"role": "user", "content": text},
            ],
            response_format=CleanedText,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error in get_command: {e}")
        raise


def transcribe_audio(audio_file, clipboard_content=None):
    """Transcribe audio file using the pre-loaded whisper model with automatic CPU fallback"""
    global current_device

    try:
        logger.info(f"Transcribing audio file: {audio_file}")
        result = model.transcribe(audio_file)
        text = result["text"].strip() + " "

        # Add subtle indicator for CPU usage (extra dot)
        if current_device == "cpu":
            text += "."

        if clipboard_content:
            param = f"<context>{clipboard_content}</context> <command>{text}</command>"
            response = get_command(param)
            return response.response
        else:
            return text
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error transcribing audio: {error_str}")

        # Check if it's a CUDA error and we're currently using GPU
        if ("CUDA" in error_str or "unspecified launch failure" in error_str) and current_device == "cuda":
            logger.warning("CUDA error detected - attempting CPU fallback")

            # Try to reload model on CPU
            if reload_model_on_device("cpu"):
                logger.info("Successfully fell back to CPU - retrying transcription")
                try:
                    # Retry transcription with CPU model
                    result = model.transcribe(audio_file)
                    text = result["text"].strip() + " "

                    # Add subtle indicator for CPU usage (extra dot)
                    text += "."

                    if clipboard_content:
                        param = f"<context>{clipboard_content}</context> <command>{text}</command>"
                        response = get_command(param)
                        return response.response
                    else:
                        return text
                except Exception as cpu_error:
                    logger.error(f"CPU transcription also failed: {cpu_error}")
                    return f"Error transcribing (both GPU and CPU failed): {str(cpu_error)}"
            else:
                logger.error("Failed to reload model on CPU")
                return f"Error transcribing: {error_str}"
        else:
            return f"Error transcribing: {error_str}"


def handle_client(client_socket):
    """Handle client connection and transcription request"""
    try:
        logger.info("Handling new client connection")
        # Receive the request
        data = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            # Check if we have a complete message
            if data.endswith(b"\n\n"):
                break

        request = json.loads(data.decode("utf-8").strip())
        audio_file = request.get("audio_file")
        clipboard_content = request.get("clipboard_content")

        # Process the transcription
        result = transcribe_audio(audio_file, clipboard_content)

        # Send the response
        client_socket.sendall(json.dumps({"result": result}).encode("utf-8"))
        logger.info("Successfully processed client request")
    except Exception as e:
        logger.error(f"Error handling client: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            client_socket.sendall(json.dumps({"error": str(e)}).encode("utf-8"))
        except:
            pass
    finally:
        client_socket.close()


def main():
    """Main server loop"""
    try:
        # Remove socket if it already exists
        if os.path.exists(SERVER_SOCKET):
            os.unlink(SERVER_SOCKET)

        # Create a socket
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SERVER_SOCKET)
        server.listen(5)

        # Set up signal handlers for graceful shutdown
        def handle_signal(sig, frame):
            logger.info("Received shutdown signal")
            print("Shutting down...")
            server.close()
            if os.path.exists(SERVER_SOCKET):
                os.unlink(SERVER_SOCKET)
            if os.path.exists(PID_FILE):
                os.unlink(PID_FILE)
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        logger.info(f"Server started at {SERVER_SOCKET}")
        print(f"Server started at {SERVER_SOCKET}")

        # Server loop
        while True:
            try:
                client_socket, _ = server.accept()
                handle_client(client_socket)
            except Exception as e:
                logger.error(f"Error in server loop: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue running even if one request fails
                continue

    except Exception as e:
        logger.error(f"Fatal server error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
