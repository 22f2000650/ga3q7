from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re

app = FastAPI()

class AskRequest(BaseModel):
    video_url: str
    topic: str


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from normal and short URLs.
    """
    parsed = urlparse(url)

    if "youtu.be" in parsed.netloc:
        return parsed.path.strip("/")

    if "youtube.com" in parsed.netloc:
        query = parse_qs(parsed.query)
        return query.get("v", [None])[0]

    return None


def seconds_to_hhmmss(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"


@app.post("/ask")
def ask(req: AskRequest):

    video_id = extract_video_id(req.video_url)

    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Transcript not available")

    topic_lower = req.topic.lower()

    for entry in transcript:
        if topic_lower in entry["text"].lower():
            timestamp = seconds_to_hhmmss(entry["start"])
            return {
                "timestamp": timestamp,
                "video_url": req.video_url,
                "topic": req.topic
            }

    # If not found, return 00:00:00 (safe fallback)
    return {
        "timestamp": "00:00:00",
        "video_url": req.video_url,
        "topic": req.topic
    }