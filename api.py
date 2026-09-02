import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp
import database

app = FastAPI(title="Ronak Fast API")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup():
    await database.init_db()

def delete_file(path: str):
    if os.path.exists(path):
        try: os.remove(path)
        except: pass

@app.get("/download")
async def download_media(url: str, type: str, api_key: str, background_tasks: BackgroundTasks):
    # 1. API Key और 30-Day Expiry चेक करें
    is_valid, msg = await database.verify_key(api_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)

    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url

    # 2. ऑडियो और वीडियो के लिए अलग-अलग हाई-स्पीड सेटिंग्स
    if type == "video":
        ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/{video_id}.mp4', 'quiet': True}
    else:
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f'{DOWNLOAD_DIR}/{video_id}.mp3', 'quiet': True}

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_id, download=True)
            return ydl.prepare_filename(info)

    try:
        filename = await asyncio.to_thread(extract)
        background_tasks.add_task(delete_file, filename) # स्ट्रीम होने के बाद आटोमेटिक डिलीट
        return FileResponse(filename, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
