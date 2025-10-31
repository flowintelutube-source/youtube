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

def dl(vid):
    url = f"https://www.youtube.com/watch?v={vid}"
    subprocess.run([
        "yt-dlp",
        "--quiet", "--no-warnings",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "-f", "best[height<=720]", "-o", "cc.mp4", url
    ], check=True)

def transcribe():
    model = whisper.load_model("base")
    result = model.transcribe("cc.mp4")
    text = result["text"][:500]
    Path("summary.txt").write_text(text, encoding="utf8")
    return text

def thumb():
    img = Image.new("RGB", (1280, 720), "black")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        font = ImageFont.load_default()
    d.text((100, 300), "HISTOIRE\nVRAIE", font=font, fill="white")
    img.save("thumb.jpg")

async def tts():
    await edge_tts.Communicate(Path("summary.txt").read_text(), "fr-FR-DeniseNeural").save("voice.mp3")

def edit():
    video = mp.VideoFileClip("cc.mp4").subclip(0, 58)
    audio = mp.AudioFileClip("voice.mp3")
    mp.VideoFileClip("cc.mp4").subclip(0, 58).set_audio(audio).write_videofile("final.mp4", logger=None)

def upload():
    body = {
        "snippet": {
            "title": "Histoire vraie en 60 s 🔥 #Shorts",
            "description": "Résumé IA – lien original dans les commentaires.",
            "tags": ["shorts", "histoire", "ia"],
            "categoryId": "24"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload("final.mp4", chunksize=-1, resumable=True)
    r = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    youtube.thumbnails().set(videoId=r["id"], media_body=MediaFileUpload("thumb.jpg")).execute()

def main():
    vid = search_cc()
    if not vid:
        print("Aucune vidéo CC trouvée.")
        return
    dl(vid)
    transcribe()
    asyncio.run(tts())
    edit()
    thumb()
    upload()

if __name__ == "__main__":
    main()
