import os
import sys
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# ------------------------------------------------------------------
# Environment validation
# ------------------------------------------------------------------
PEXELS_API_KEY: Optional[str] = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    logging.error("❌ PEXELS_API_KEY environment variable is not set.")
    sys.exit(1)

logging.info("🔑 Pexels API key found (%s...)", PEXELS_API_KEY[:5])

# ------------------------------------------------------------------
# Core logic
# ------------------------------------------------------------------
def search_cc() -> str:
    """
    Fetch a Creative-Commons video URL from Pexels.
    Replace this stub with actual Pexels API logic.
    """
    import requests

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": "nature",
        "orientation": "landscape",
        "size": "medium",
        "per_page": 1,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logging.error("❌ Pexels API request failed: %s", exc)
        sys.exit(1)

    data = resp.json()
    try:
        video_url = data["videos"][0]["video_files"][0]["link"]
        logging.info("✅ Found CC video: %s", video_url)
        return video_url
    except (IndexError, KeyError):
        logging.error("❌ No suitable Creative-Commons video found.")
        sys.exit(1)

# ------------------------------------------------------------------
# Main entrypoint
# ------------------------------------------------------------------
def main() -> None:
    url = search_cc()
    logging.info("🎯 Selected video URL: %s", url)

def search_cc():
    url = "https://api.pexels.com/videos/search"
    params = {"query": "story", "per_page": 20}
    h = {"Authorization": PEXELS_KEY}
    print("🔑 Clé Pexels reçue :", PEXELS_KEY[:5], "...")
    r = requests.get(url, headers=h, params=params, timeout=10)
    print("📡 Status Pexels :", r.status_code)
    print("📄 Réponse brute :", r.text[:200])
    if r.status_code != 200:
        return None
    videos = r.json().get("videos", [])
    if not videos:
        return None
    pick = random.choice(videos)
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
