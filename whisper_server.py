#!/usr/bin/env python3
import os
import sys
import json
import re
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

SERVER_SOCKET = "/tmp/whisper_server.sock"
PID_FILE = "/tmp/whisper_server.pid"


def other_server_pid():
    """Return the PID of another live whisper server, or None"""
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if pid == os.getpid():
            return None
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            if b"whisper_server.py" in f.read():
                return pid
    except (OSError, ValueError):
        pass
    return None


# Refuse to start a second server: two copies of the model don't fit on the GPU
if __name__ == "__main__" and other_server_pid():
    logger.info(f"Whisper server already running (PID {other_server_pid()}), exiting")
    sys.exit(0)

# Write PID file early so a server that is still loading the model blocks duplicates
with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

# Check for required packages
required_packages = {
    "whisper": "openai-whisper",
    "silero_vad": "silero-vad",
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
from silero_vad import load_silero_vad, get_speech_timestamps
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

MODEL_NAME = "turbo"

# Domain vocabulary fed to Whisper as initial_prompt to bias spelling of technical terms
VOCAB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.txt")


def load_vocab_prompt():
    try:
        with open(VOCAB_FILE) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        logger.warning(f"Vocab file not found: {VOCAB_FILE}")
        return None
    prose = [line[2:] for line in lines if line.startswith("> ")]
    terms = [line for line in lines if not line.startswith("> ")]
    logger.info(f"Loaded {len(terms)} vocab terms")
    return " ".join(prose + [", ".join(terms) + "."])


VOCAB_PROMPT = load_vocab_prompt()

# Misrecognitions the prompt can't fully prevent; only unambiguous phrases, since bare "cloud" is a real word
CORRECTIONS = [
    (re.compile(r"\b(?:cloud|claude)\.md\b", re.IGNORECASE), "CLAUDE.md"),
    (re.compile(r"\b(?:cloud|claude) code\b", re.IGNORECASE), "Claude Code"),
]


def apply_corrections(text):
    for pattern, replacement in CORRECTIONS:
        text = pattern.sub(replacement, text)
    return text


def load_model(target_device):
    """Load the model; on GPU keep fp16 weights (~1.6 GB) instead of whisper's default fp32 (~3.2 GB)"""
    if target_device == "cpu":
        return whisper.load_model(MODEL_NAME, device="cpu")
    m = whisper.load_model(MODEL_NAME, device="cpu").half()
    # whisper's LayerNorm runs in fp32 and expects fp32 weights
    for module in m.modules():
        if isinstance(module, torch.nn.LayerNorm):
            module.float()
    return m.to(target_device)


# Load the whisper model once at startup (this is the key optimization)
print(f"Loading whisper model '{MODEL_NAME}' on {device}...")
model = load_model(device)
current_device = device
print("Model loaded and ready!")

# Whisper hallucinates on silence and room noise, so only speech regions found by the VAD are transcribed
vad_model = load_silero_vad()
SAMPLE_RATE = 16000


def load_speech(audio_file):
    """Return the audio with non-speech removed, or None if the recording has no speech"""
    audio = torch.from_numpy(whisper.load_audio(audio_file))
    timestamps = get_speech_timestamps(audio, vad_model, sampling_rate=SAMPLE_RATE, speech_pad_ms=200)
    if not timestamps:
        return None
    # Keep a short pause between speech chunks so Whisper doesn't run words together across them
    gap = torch.zeros(int(0.3 * SAMPLE_RATE))
    chunks = []
    for ts in timestamps:
        chunks += [audio[ts["start"]:ts["end"]], gap]
    return torch.cat(chunks[:-1]).numpy()


# Function to reload model on different device
def reload_model_on_device(target_device):
    """Reload whisper model on specified device"""
    global model, current_device
    try:
        logger.info(f"Reloading model on {target_device} device")
        model = load_model(target_device)
        current_device = target_device
        logger.info(f"Model successfully reloaded on {target_device}")
        return True
    except Exception as e:
        logger.error(f"Failed to reload model on {target_device}: {e}")
        return False



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
        audio = load_speech(audio_file)
        if audio is None:
            logger.info("No speech detected, skipping transcription")
            return ""
        result = model.transcribe(audio, language="en", initial_prompt=VOCAB_PROMPT)
        text = apply_corrections(result["text"].strip()) + " "

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
                    result = model.transcribe(audio, language="en", initial_prompt=VOCAB_PROMPT)
                    text = apply_corrections(result["text"].strip()) + " "

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
        socket_inode = os.stat(SERVER_SOCKET).st_ino

        # Set up signal handlers for graceful shutdown
        def handle_signal(sig, frame):
            logger.info("Received shutdown signal")
            print("Shutting down...")
            server.close()
            # Only remove the socket and PID file if they are still ours, not a newer server's
            try:
                if os.stat(SERVER_SOCKET).st_ino == socket_inode:
                    os.unlink(SERVER_SOCKET)
            except OSError:
                pass
            if other_server_pid() is None and os.path.exists(PID_FILE):
                os.unlink(PID_FILE)
            # os._exit, not sys.exit: SystemExit can be swallowed mid-request, leaving the
            # process spinning on the closed socket while still holding GPU memory
            os._exit(0)

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
                if server.fileno() == -1:
                    logger.error("Server socket closed, exiting")
                    os._exit(1)
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
