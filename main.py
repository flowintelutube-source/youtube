import os, datetime, subprocess, whisper, moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import edge_tts, asyncio
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
import requests, random

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)

# SOURCE SAFE : Archive.org Creative Commons vidéos
def search_cc():
    # 50 films publics / CC récents sur Archive.org
    base = "https://archive.org/advancedsearch.php"
    params = {
        "q": "creativecommons AND (crime OR story OR survival) AND mediatype:movies",
        "fl": "identifier,title", "rows": 50, "output": "json"
    }
    r = requests.get(base, params=params, headers={"Referer": "https://github.com"})
    if r.status_code != 200: return None
    items = r.json().get("response", {}).get("docs", [])
    if not items: return None
    pick = random.choice(items)
    return "https://archive.org/download/" + pick["identifier"] + "/" + pick["identifier"] + "_512kb.mp4"

def dl(url):
    # téléchargement direct (no bot-check)
    subprocess.run(["wget", "-q", "-O", "cc.mp4", url], check=True)

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
            "description": "Résumé IA – vidéo libre de droits (Archive.org).",
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
        print("Aucune vidéo CC trouvée.")
        return
    dl(url)
    transcribe()
    asyncio.run(tts())
    edit()
    thumb()
    upload()

if __name__ == "__main__":
    main()
