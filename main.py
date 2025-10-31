import os, datetime, subprocess, whisper, moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import edge_tts, asyncio
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
import requests

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)

def search_cc():
    from datetime import datetime, timedelta
    date = (datetime.utcnow() - timedelta(days=7)).isoformat("T") + "Z"
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        "?q=story&part=snippet&type=video&videoLicense=creativeCommon"
        "&order=viewCount&publishedAfter=" + date +
        "&maxResults=10&key=" + API_KEY
    )
    headers = {"Referer": "https://github.com"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    res = r.json()
    for v in res["items"]:
        vid = v["id"]["videoId"]
        stats = youtube.videos().list(part="statistics", id=vid).execute()["items"][0]["statistics"]
        if int(stats.get("viewCount", 0)) > 50_000:
            return vid
    return None
