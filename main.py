#!/usr/bin/env python3
"""
auto_shorts.py
Génère un Shorts YouTube à partir d’une vidéo Pexels (libre de droits).
Dépendances :
    pip install whisper openai-whisper edge-tts moviepy pillow google-api-python-client python-dotenv
"""

import os, sys, random, requests, asyncio, logging, datetime as dt
from pathlib import Path
from typing import Optional

import whisper
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ---------- CONFIG ----------
DOTENV = Path(__file__).with_suffix(".env")
if DOTENV.exists():
    import dotenv, dotenv.variables
    dotenv.load_dotenv(DOTENV)

PEXELS_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY")
if not PEXELS_KEY or not YOUTUBE_KEY:
    sys.exit("❗ Variables PEXELS_API_KEY et YOUTUBE_API_KEY requises.")
    
# ---------- CONFIG ----------
DOTENV = Path(__file__).with_suffix(".env")
if DOTENV.exists():
    import dotenv
    dotenv.load_dotenv(DOTENV)

PEXELS_KEY  = os.getenv("PEXELS_API_KEY")
YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY")

# Vérification rapide
if not PEXELS_KEY or not YOUTUBE_KEY:
    print("❗ Variables PEXELS_API_KEY et YOUTUBE_API_KEY requises.")
    sys.exit(1)
# ---------- UTILS ----------
def safe_filename(stem: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in stem)

def download(url: str, dest: Path, chunk_mb: int = 2) -> bool:
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_mb * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
        log.info("✅ Téléchargé : %s", dest.name)
        return True
    except Exception as exc:
        log.error("❌ Échec téléchargement %s : %s", url, exc)
        return False

# ---------- PEXELS ----------
def pick_pexels_video(query: str = "story") -> Optional[str]:
    url = "https://api.pexels.com/videos/search"
    params = {"query": query, "per_page": 20, "orientation": "portrait"}
    headers = {"Authorization": PEXELS_KEY}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
    except Exception as exc:
        log.error("❌ Pexels API : %s", exc)
        return None

    videos = r.json().get("videos", [])
    if not videos:
        log.warning("⚠️ Aucune vidéo Pexels pour %s", query)
        return None

    pick = random.choice(videos)
    for f in pick["video_files"]:
        if f.get("quality") == "hd" and f.get("file_type") == "video/mp4":
            return f["link"]
    return None

# ---------- WHISPER ----------
def transcribe(video_path: Path) -> str:
    model = whisper.load_model("base")
    result = model.transcribe(str(video_path))
    text = result["text"].strip()[:500]
    (TEMP_DIR / "summary.txt").write_text(text, encoding="utf-8")
    log.info("🎤 Transcription : %s...", text[:60])
    return text

# ---------- TTS ----------
async def generate_voice(text: str) -> bool:
    communicate = edge_tts.Communicate(text, "fr-FR-DeniseNeural")
    out = TEMP_DIR / "voice.mp3"
    await communicate.save(str(out))
    if out.stat().st_size == 0:
        log.error("❌ TTS a généré un fichier vide")
        return False
    log.info("✅ Voix générée")
    return True

# ---------- MONTAGE ----------
def build_final(target_duration: int = 58) -> Optional[Path]:
    video_path = TEMP_DIR / "cc.mp4"
    voice_path = TEMP_DIR / "voice.mp3"
    final_path = TEMP_DIR / "final.mp4"

    if not video_path.exists() or not voice_path.exists():
        log.error("❌ Fichiers sources manquants")
        return None

    try:
        video = mp.VideoFileClip(str(video_path))
        audio = mp.AudioFileClip(str(voice_path))

        # Coupe la vidéo si trop longue
        if video.duration > target_duration:
            video = video.subclip(0, target_duration)

        # Ajuste l’audio si besoin
        if audio.duration > target_duration:
            audio = audio.subclip(0, target_duration)

        final = video.set_audio(audio)
        final.write_videofile(str(final_path), logger=None, codec="libx264", audio_codec="aac")
        video.close(); audio.close(); final.close()
        log.info("✅ Montage finalisé")
        return final_path
    except Exception as exc:
        log.error("❌ Erreur montage : %s", exc)
        return None

# ---------- THUMBNAIL ----------
def make_thumb() -> Path:
    thumb_path = TEMP_DIR / "thumb.jpg"
    img = Image.new("RGB", (1280, 720), "black")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    draw.text((100, 300), "HISTOIRE\nVRAIE", font=font, fill="white")
    img.save(thumb_path, quality=95)
    log.info("✅ Miniature créée")
    return thumb_path

# ---------- UPLOAD ----------
def upload_to_youtube(video_path: Path, thumb_path: Path) -> bool:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_KEY, cache_discovery=False)
    body = {
        "snippet": {
            "title": "Histoire vraie en 60 s 🔥 #Shorts",
            "description": "Résumé IA – vidéo libre de droits (Pexels).",
            "tags": ["shorts", "histoire", "ia"],
            "categoryId": "24",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    try:
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        youtube.thumbnails().set(videoId=response["id"], media_body=MediaFileUpload(thumb_path)).execute()
        log.info("✅ Upload OK – ID : %s", response["id"])
        return True
    except HttpError as e:
        log.error("❌ Upload YouTube : %s", e.content.decode())
        return False

# ---------- PIPELINE ----------
def main() -> None:
    log.info("========== Début pipeline ==========")

    # 1. Vidéo
    url = pick_pexels_video()
    if not url:
        log.error("❌ Impossible de récupérer une vidéo Pexels")
        return
    video_file = TEMP_DIR / "cc.mp4"
    if not download(url, video_file):
        return

    # 2. Transcription
    text = transcribe(video_file)

    # 3. Voix
    if not asyncio.run(generate_voice(text)):
        return

    # 4. Montage
    final_video = build_final()
    if not final_video:
        return

    # 5. Miniature
    thumb = make_thumb()

    # 6. Upload
    upload_to_youtube(final_video, thumb)
    log.info("========== Pipeline terminé ==========")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("Interrompu par l’utilisateur")
