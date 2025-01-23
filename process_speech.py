#!/usr/bin/env python3
import sys
import os, dotenv
from pydantic import BaseModel
from openai import OpenAI

dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CleanedText(BaseModel):
    thoughts: str
    response: str

def transcribe_with_whisper(audio_file):
    import whisper
    model = whisper.load_model("small.en")  # or "small", "medium", "large", etc.
    result = model.transcribe(audio_file)
    text = result["text"]
    return text.strip()

def clean_text(text):
    completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Clean up any filler words, punctuation, and other noise from the text."},
        {"role": "user", "content": text},
    ],
    response_format=CleanedText)
    var =  completion.choices[0].message.parsed
    return var

def get_command(text):
    completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that can help me with my tasks. I will give you some context and a command. respond appropriately. If there is a linux shell prompt in the context, respond with the command to execute the request and nothing else. not even the ~."},
        {"role": "user", "content": text},
    ],
    response_format=CleanedText)
    var =  completion.choices[0].message.parsed
    return var


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: process_speech.py <audio.wav> [clipboard_content]")
        sys.exit(1)

    audio_file = sys.argv[1]
    text = transcribe_with_whisper(audio_file)

    if len(sys.argv) == 2:
        # Original behavior for single argument
        print(text)
    else:
        # New behavior for two arguments - wrap in XML tags
        clipboard_content = sys.argv[2]
        param=f"<context>{clipboard_content}</context> \
            <command>{text}</command>"
        response = get_command(param)
        print(response.response)
