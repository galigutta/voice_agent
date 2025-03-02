import sys
try:
    import whisper
except ImportError as e:
    print(f"Error: Required modules not found: {e}")
    sys.exit(1)

