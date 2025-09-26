#!/usr/bin/env python3
import sys
import os
import dotenv
from pydantic import BaseModel
from openai import OpenAI

dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TerminalCommand(BaseModel):
    thoughts: str
    command: str

def convert_to_terminal_command(transcribed_text, selected_text=None):
    """Convert transcribed text to Ubuntu terminal command, optionally using selected text as context"""

    system_prompt = """You are a voice-to-command converter for Ubuntu Linux terminal.
    Convert the user's spoken request into the appropriate terminal command.
    Output ONLY the command, no explanations, no comments, no markdown.

    Examples:
    - "list all files" → ls -la
    - "show current directory" → pwd
    - "create a new folder called test" → mkdir test
    - "search for python files" → find . -name "*.py"
    - "check disk usage" → df -h
    - "show running processes" → ps aux
    - "edit the readme file" → nano README.md
    - "install docker" → sudo apt-get install docker.io
    - "show network connections" → netstat -tuln
    - "check system info" → uname -a

    Context-aware examples (when text is selected):
    - Selected: "example.py", User says: "delete this" → rm example.py
    - Selected: "mydir", User says: "go into this folder" → cd mydir
    - Selected: "package-name", User says: "install this" → sudo apt-get install package-name
    - Selected: "8080", User says: "kill process on this port" → sudo kill $(sudo lsof -t -i:8080)

    Clean up any filler words and interpret the intent correctly."""
    
    # Build the input prompt with optional selected text context
    if selected_text:
        input_prompt = f"{system_prompt}\n\nSelected text: {selected_text}\nUser request: {transcribed_text}"
    else:
        input_prompt = f"{system_prompt}\n\nUser request: {transcribed_text}"

    try:
        response = client.responses.create(
            model="gpt-5",
            input=input_prompt,
            reasoning={
                "effort": "low"
            }
        )
        # Extract the text from the response output
        for item in response.output:
            if hasattr(item, 'content') and item.content:
                for content_item in item.content:
                    if hasattr(content_item, 'text'):
                        return content_item.text.strip()
        # Fallback if structure is unexpected
        return transcribed_text
    except Exception:
        # If GPT processing fails, return the original text
        return transcribed_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: process_with_gpt.py <transcribed_text> [selected_text]")
        sys.exit(1)

    transcribed_text = sys.argv[1]
    selected_text = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_to_terminal_command(transcribed_text, selected_text)
    print(result)