import os
import re
import time
import yt_dlp
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# Set your Gemini API key as environment variable
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class AskRequest(BaseModel):
    video_url: str
    topic: str

def download_audio(url, filename="audio.mp3"):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filename,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return filename

def extract_timestamp(text):
    match = re.search(r'\b\d{2}:\d{2}:\d{2}\b', text)
    return match.group(0) if match else "00:00:00"

@app.post("/ask")
def ask(req: AskRequest):
    audio_file = download_audio(req.video_url)

    # Upload file to Gemini
    file = genai.upload_file(audio_file)

    # Wait until file is ACTIVE
    while file.state.name != "ACTIVE":
        time.sleep(2)
        file = genai.get_file(file.name)

    model = genai.GenerativeModel("gemini-1.5-pro")

    response = model.generate_content(
        [
            file,
            f"Find the first time the topic '{req.topic}' is spoken in this audio. "
            "Return ONLY the timestamp in HH:MM:SS format."
        ]
    )

    timestamp = extract_timestamp(response.text)

    os.remove(audio_file)

    return {
        "timestamp": timestamp,
        "video_url": req.video_url,
        "topic": req.topic
    }