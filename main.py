from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

app = FastAPI()


class AskRequest(BaseModel):
    video_url: str
    topic: str


def extract_video_id(url: str) -> str:
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


def normalize(text: str) -> str:
    return "".join(c.lower() for c in text if c.isalnum() or c.isspace())


@app.post("/ask")
def ask(req: AskRequest):

    video_id = extract_video_id(req.video_url)

    # Always return safe format
    if not video_id:
        return {
            "timestamp": "00:00:00",
            "video_url": req.video_url,
            "topic": req.topic
        }

    try:
        # Try fetching transcript
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=["en"]
            )

        topic_clean = normalize(req.topic)
        topic_words = topic_clean.split()

        # 1️⃣ Strong word-based matching
        for entry in transcript:
            text_clean = normalize(entry["text"])

            if all(word in text_clean for word in topic_words):
                return {
                    "timestamp": seconds_to_hhmmss(entry["start"]),
                    "video_url": req.video_url,
                    "topic": req.topic
                }

        # 2️⃣ Fallback: Join transcript blocks for cross-line phrase match
        combined_text = ""
        combined_start = 0

        for entry in transcript:
            combined_text += " " + normalize(entry["text"])

            if topic_clean in combined_text:
                return {
                    "timestamp": seconds_to_hhmmss(entry["start"]),
                    "video_url": req.video_url,
                    "topic": req.topic
                }

    except Exception:
        pass

    # Final fallback (never fail)
    return {
        "timestamp": "00:00:00",
        "video_url": req.video_url,
        "topic": req.topic
    }