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

def convert_to_terminal_command(transcribed_text):
    """Convert transcribed text to Ubuntu terminal command"""
    
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
    
    Clean up any filler words and interpret the intent correctly."""
    
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcribed_text},
            ],
            response_format=TerminalCommand
        )
        result = completion.choices[0].message.parsed
        return result.command
    except Exception:
        # If GPT processing fails, return the original text
        return transcribed_text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: process_with_gpt.py <transcribed_text>")
        sys.exit(1)
    
    transcribed_text = sys.argv[1]
    
    result = convert_to_terminal_command(transcribed_text)
    print(result)