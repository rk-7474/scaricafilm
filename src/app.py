import asyncio
import json
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from src.config import settings_manager
from src.scraper import scraper
from src.downloader import download_manager, DownloadTask

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ScaricaFilm WebUI", description="WebUI per scaricare film e serie da StreamingCommunity")

# Mount static and templates
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.on_event("startup")
async def startup_event():
    download_manager.start_worker()

# --- Schemas ---
class DownloadMovieRequest(BaseModel):
    title_id: int
    title_name: str
    media_type: str = "movie"
    year: str = ""
    quality: Optional[str] = None
    audio_lang: Optional[str] = None
    poster_url: Optional[str] = None

class DownloadEpisodeRequest(BaseModel):
    title_id: int
    title_name: str
    media_type: str = "tv"
    year: str = ""
    episode_id: int
    season_number: int
    episode_number: int
    episode_name: str
    quality: Optional[str] = None
    audio_lang: Optional[str] = None
    poster_url: Optional[str] = None

class DownloadSeasonRequest(BaseModel):
    title_id: int
    title_name: str
    year: str = ""
    season_number: int
    episodes: List[dict]
    quality: Optional[str] = None
    audio_lang: Optional[str] = None
    poster_url: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    streamingcommunity_url: Optional[str] = None
    download_dir: Optional[str] = None
    preferred_quality: Optional[str] = None
    preferred_audio: Optional[str] = None
    max_concurrent_downloads: Optional[int] = None

# --- HTML Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"settings": settings_manager.all()}
    )

# --- API Routes ---
@app.get("/api/search")
async def search(q: str = Query(..., min_length=1)):
    try:
        results = await asyncio.to_thread(scraper.search_titles, q)
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e), "results": []}

@app.get("/api/titles/{title_id}")
async def title_details(title_id: int, slug: str = Query(...)):
    try:
        details = await asyncio.to_thread(scraper.get_title_details, title_id, slug)
        return {"ok": True, "details": details}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/titles/{title_id}/season/{season_num}")
async def season_episodes(title_id: int, season_num: int, slug: str = Query(...)):
    try:
        episodes = await asyncio.to_thread(scraper.get_season_episodes, title_id, slug, season_num)
        return {"ok": True, "episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download/movie")
async def download_movie(req: DownloadMovieRequest):
    task = DownloadTask(
        title_id=req.title_id,
        title_name=req.title_name,
        media_type="movie",
        year=req.year,
        quality=req.quality,
        audio_lang=req.audio_lang,
        poster_url=req.poster_url
    )
    task_id = await download_manager.add_task(task)
    return {"ok": True, "task_id": task_id, "message": f"'{req.title_name}' aggiunto alla coda"}

@app.post("/api/download/episode")
async def download_episode(req: DownloadEpisodeRequest):
    task = DownloadTask(
        title_id=req.title_id,
        title_name=req.title_name,
        media_type="tv",
        year=req.year,
        episode_id=req.episode_id,
        season_number=req.season_number,
        episode_number=req.episode_number,
        episode_name=req.episode_name,
        quality=req.quality,
        audio_lang=req.audio_lang,
        poster_url=req.poster_url
    )
    task_id = await download_manager.add_task(task)
    return {"ok": True, "task_id": task_id, "message": f"Episodio {req.season_number}x{req.episode_number} aggiunto alla coda"}

@app.post("/api/download/season")
async def download_season(req: DownloadSeasonRequest):
    task_ids = []
    for ep in req.episodes:
        task = DownloadTask(
            title_id=req.title_id,
            title_name=req.title_name,
            media_type="tv",
            year=req.year,
            episode_id=ep.get("id"),
            season_number=req.season_number,
            episode_number=ep.get("number"),
            episode_name=ep.get("name"),
            quality=req.quality,
            audio_lang=req.audio_lang,
            poster_url=req.poster_url
        )
        t_id = await download_manager.add_task(task)
        task_ids.append(t_id)

    return {"ok": True, "task_ids": task_ids, "message": f"{len(task_ids)} episodi aggiunti alla coda"}

@app.get("/api/downloads")
async def get_downloads():
    return {"ok": True, "tasks": download_manager.get_all_tasks()}

@app.post("/api/downloads/{task_id}/cancel")
async def cancel_download(task_id: str):
    success = download_manager.cancel_task(task_id)
    return {"ok": success}

@app.delete("/api/downloads/{task_id}")
async def delete_download(task_id: str, delete_file: bool = Query(False)):
    success = download_manager.delete_task(task_id, delete_file=delete_file)
    return {"ok": success}

@app.get("/api/downloads/stream")
async def stream_downloads():
    async def event_generator():
        while True:
            tasks = download_manager.get_all_tasks()
            yield f"data: {json.dumps(tasks)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Settings ---
@app.get("/api/settings")
async def get_settings():
    return {"ok": True, "settings": settings_manager.all()}

@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    updates = {k: v for k, v in req.dict().items() if v is not None}
    saved = settings_manager.update(updates)
    return {"ok": True, "settings": saved, "message": "Impostazioni salvate con successo"}

@app.post("/api/settings/test")
async def test_settings_connection(req: dict):
    url = req.get("streamingcommunity_url")
    result = await asyncio.to_thread(scraper.test_connection, url)
    return result
