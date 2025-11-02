import os, datetime, whisper, moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import edge_tts, asyncio
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
import requests, random

API_KEY   = os.getenv("YOUTUBE_API_KEY")
PEXELS_KEY= os.getenv("PEXELS_API_KEY")
youtube   = build("youtube", "v3", developerKey=API_KEY)

def search_cc():
    url = "https://api.pexels.com/videos/search"
    params = {"query": "story", "per_page": 20}
    h = {"Authorization": PEXELS_KEY}
    r = requests.get(url, headers=h, params=params)
    if r.status_code != 200: return None
    videos = r.json().get("videos", [])
    if not videos: return None
    pick = random.choice(videos)
    # prend le fichier HD
    for f in pick["video_files"]:
        if f["quality"] == "hd" and f["file_type"] == "video/mp4":
            return f["link"]
    return None

def dl(url):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open("cc.mp4", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk: f.write(chunk)

def transcribe():
    model = whisper.load_model("base")
    result = model.transcribe("cc.mp4")
    text = result["text"][:500]
    Path("summary.txt").write_text(text, encoding="utf8")
    return text

def thumb():
    img = Image.new("RGB", (1280, 720), "black")
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arial.ttf", 120)
    except: font = ImageFont.load_default()
    d.text((100, 300), "HISTOIRE\nVRAIE", font=font, fill="white")
    img.save("thumb.jpg")

async def tts():
    await edge_tts.Communicate(Path("summary.txt").read_text(), "fr-FR-DeniseNeural").save("voice.mp3")

def edit():
    video = mp.VideoFileClip("cc.mp4").subclip(0, 58)
    audio = mp.AudioFileClip("voice.mp3")
    video.set_audio(audio).write_videofile("final.mp4", logger=None)

def upload():
    body = {
        "snippet": {
            "title": "Histoire vraie en 60 s 🔥 #Shorts",
            "description": "Résumé IA – vidéo libre de droits (Pexels).",
            "tags": ["shorts", "histoire", "ia"],
            "categoryId": "24"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload("final.mp4", chunksize=-1, resumable=True)
    r = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    youtube.thumbnails().set(videoId=r["id"], media_body=MediaFileUpload("thumb.jpg")).execute()

def main():
    url = search_cc()
    if not url:
        print("Aucune vidéo Pexels trouvée.")
        return
    dl(url)
    transcribe()
    asyncio.run(tts())
    edit()
    thumb()
    upload()

if __name__ == "__main__":
    main()
