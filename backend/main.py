from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    print("Error: youtube_transcript_api not installed properly.")
    print("Please run: pip install youtube-transcript-api --upgrade")
    raise

import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update this with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')


class VideoURL(BaseModel):
    url: str


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=([^&]+)',
        r'^https?://(?:www\.)?youtube\.com/v/([^/?]+)',
        r'^https?://youtu\.be/([^/?]+)'
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_id: str) -> str:
    """Get video transcript using youtube_transcript_api."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript_list])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise HTTPException(status_code=404, detail="Transcript not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_summary(transcript: str) -> str:
    """Generate summary using Gemini AI."""
    try:
        prompt = f"""
        Please provide a comprehensive summary of the following video transcript. 
        Format the response as follows:

        # Main Points
        * Key point 1
        * Key point 2
        * Key point 3

        # Detailed Summary
        A paragraph or two providing a more detailed overview of the content.

        # Key Takeaways
        * Important takeaway 1
        * Important takeaway 2
        * Important takeaway 3

        Transcript:
        {transcript}
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@app.post("/api/summarize")
async def summarize_video(video: VideoURL):
    """Endpoint to summarize YouTube video."""
    video_id = extract_video_id(video.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    transcript = get_transcript(video_id)
    summary = generate_summary(transcript)

    return {"summary": summary}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)