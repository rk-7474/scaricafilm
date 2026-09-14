import os
import re
import time
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.config import settings_manager
from src.scraper import scraper

def sanitize_filename(name: str) -> str:
    # Replace illegal characters for filesystem
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized or "media"

def format_time(seconds: float) -> str:
    if seconds < 0:
        return "0s"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"

def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    for fallback in [
        "/home/giulio/.local/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "/bin/ffmpeg"
    ]:
        if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
            return fallback
    return "ffmpeg"

class DownloadTask:
    def __init__(
        self,
        title_id: int,
        title_name: str,
        media_type: str = "movie",
        year: str = "",
        episode_id: Optional[int] = None,
        season_number: Optional[int] = None,
        episode_number: Optional[int] = None,
        episode_name: Optional[str] = None,
        quality: Optional[str] = None,
        audio_lang: Optional[str] = None,
        poster_url: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.title_id = title_id
        self.title_name = title_name
        self.media_type = media_type
        self.year = year
        self.episode_id = episode_id
        self.season_number = season_number
        self.episode_number = episode_number
        self.episode_name = episode_name
        self.quality = quality or settings_manager.get("preferred_quality", "1080p")
        self.audio_lang = audio_lang or settings_manager.get("preferred_audio", "ita")
        self.poster_url = poster_url

        self.status = "queued"  # queued, resolving, downloading, completed, failed, cancelled
        self.progress = 0.0
        self.speed = "0x"
        self.eta = "--"
        self.downloaded_size = "0 B"
        self.total_duration = 0.0
        self.file_path = ""
        self.error_message = ""
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

        self._process: Optional[asyncio.subprocess.Process] = None
        self._part_file: Optional[Path] = None

    def get_display_title(self) -> str:
        if self.media_type == "tv" and self.season_number is not None and self.episode_number is not None:
            ep_title = f" - {self.episode_name}" if self.episode_name else ""
            return f"{self.title_name} S{self.season_number:02d}E{self.episode_number:02d}{ep_title}"
        if self.year:
            return f"{self.title_name} ({self.year})"
        return self.title_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title_id": self.title_id,
            "title_name": self.title_name,
            "display_title": self.get_display_title(),
            "media_type": self.media_type,
            "year": self.year,
            "episode_id": self.episode_id,
            "season_number": self.season_number,
            "episode_number": self.episode_number,
            "episode_name": self.episode_name,
            "quality": self.quality,
            "audio_lang": self.audio_lang,
            "poster_url": self.poster_url,
            "status": self.status,
            "progress": round(self.progress, 1),
            "speed": self.speed,
            "eta": self.eta,
            "downloaded_size": self.downloaded_size,
            "file_path": self.file_path,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

class DownloadManager:
    def __init__(self, history_file: str = "config/downloads_history.json"):
        self.tasks: Dict[str, DownloadTask] = {}
        self.history_file = Path(history_file)
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._active_count = 0
        self.load_history()

    def load_history(self):
        try:
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        t = DownloadTask(
                            title_id=item.get("title_id", 0),
                            title_name=item.get("title_name", ""),
                            media_type=item.get("media_type", "movie"),
                            year=item.get("year", ""),
                            episode_id=item.get("episode_id"),
                            season_number=item.get("season_number"),
                            episode_number=item.get("episode_number"),
                            episode_name=item.get("episode_name"),
                            quality=item.get("quality"),
                            audio_lang=item.get("audio_lang"),
                            poster_url=item.get("poster_url")
                        )
                        t.id = item.get("id", t.id)
                        t.status = item.get("status", "completed")
                        if t.status in ("downloading", "resolving", "queued"):
                            t.status = "failed"
                            t.error_message = "Download interrotto al riavvio del server"
                        t.progress = item.get("progress", 100.0 if t.status == "completed" else 0.0)
                        t.file_path = item.get("file_path", "")
                        t.downloaded_size = item.get("downloaded_size", "")
                        t.created_at = item.get("created_at", time.time())
                        t.completed_at = item.get("completed_at")
                        self.tasks[t.id] = t
        except Exception as e:
            print(f"[DownloadManager] Error loading history: {e}")

    def save_history(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            data = [t.to_dict() for t in self.tasks.values()]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[DownloadManager] Error saving history: {e}")

    def start_worker(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_queue())

    async def add_task(self, task: DownloadTask) -> str:
        self.tasks[task.id] = task
        self.save_history()
        await self.queue.put(task.id)
        self.start_worker()
        return task.id

    def cancel_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.status in ("completed", "failed", "cancelled"):
            return False

        task.status = "cancelled"
        if task._process:
            try:
                task._process.terminate()
            except Exception:
                pass

        if task._part_file and task._part_file.exists():
            try:
                task._part_file.unlink()
            except Exception:
                pass

        self.save_history()
        return True

    def delete_task(self, task_id: str, delete_file: bool = False) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status in ("downloading", "resolving"):
            self.cancel_task(task_id)

        if delete_file and task.file_path:
            p = Path(task.file_path)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

        self.tasks.pop(task_id, None)
        self.save_history()
        return True

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        # Sort by created_at descending (newest first)
        sorted_tasks = sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in sorted_tasks]

    async def _process_queue(self):
        while True:
            task_id = await self.queue.get()
            task = self.tasks.get(task_id)
            if task and task.status == "queued":
                asyncio.create_task(self._execute_download(task))
            self.queue.task_done()

    async def _execute_download(self, task: DownloadTask):
        task.status = "resolving"
        task.started_at = time.time()
        self.save_history()

        ffmpeg_bin = find_ffmpeg()
        media_root = Path(settings_manager.get("download_dir", os.path.abspath("downloads")))

        try:
            # 1. Resolve stream sources
            loop = asyncio.get_running_loop()
            sources = await loop.run_in_executor(
                None,
                scraper.extract_stream_sources,
                task.title_id,
                task.episode_id
            )

            embed_url = sources.get("embed_url")
            videos = sources.get("videos", [])
            audios = sources.get("audios", [])

            if not videos:
                raise ValueError("Nessun flusso video trovato")
            if not audios:
                raise ValueError("Nessun flusso audio trovato")

            # Select video quality
            selected_video = None
            if task.quality != "best":
                for v in videos:
                    if v.get("rendition") == task.quality:
                        selected_video = v
                        break
            if not selected_video:
                selected_video = videos[0]  # highest bitrate

            actual_quality = selected_video.get("rendition", "HD")

            # Select audio language
            selected_audio = None
            for a in audios:
                if task.audio_lang in a.get("language", "").lower() or task.audio_lang in a.get("name", "").lower():
                    selected_audio = a
                    break
            if not selected_audio:
                selected_audio = audios[0]

            video_url = selected_video["url"]
            audio_url = selected_audio["url"]

            # Calculate total duration by parsing video m3u8 extinf tags
            try:
                def get_duration():
                    r = scraper.session.get(video_url, headers={"Referer": embed_url}, timeout=10)
                    matches = re.findall(r'#EXTINF:([\d\.]+),', r.text)
                    return sum(float(x) for x in matches)
                task.total_duration = await loop.run_in_executor(None, get_duration)
            except Exception as e:
                print(f"[DownloadManager] Could not compute total duration: {e}")
                task.total_duration = 0.0

            # 2. Build destination file path
            clean_title = sanitize_filename(task.title_name)
            year_tag = f" ({task.year})" if task.year else ""

            if task.media_type == "tv" and task.season_number is not None and task.episode_number is not None:
                series_dir = media_root / "TV" / f"{clean_title}{year_tag}" / f"Season {task.season_number:02d}"
                clean_ep_name = sanitize_filename(task.episode_name or "")
                ep_suffix = f" - {clean_ep_name}" if clean_ep_name else ""
                filename = f"{clean_title} - S{task.season_number:02d}E{task.episode_number:02d}{ep_suffix} [{actual_quality}].mp4"
                final_path = series_dir / filename
            else:
                movie_dir = media_root / "Movies" / f"{clean_title}{year_tag}"
                filename = f"{clean_title}{year_tag} [{actual_quality}].mp4"
                final_path = movie_dir / filename

            final_path.parent.mkdir(parents=True, exist_ok=True)
            part_path = final_path.with_suffix(".mp4.part")
            task._part_file = part_path
            task.file_path = str(final_path)

            task.status = "downloading"
            self.save_history()

            # 3. Launch ffmpeg process
            ffmpeg_cmd = [
                ffmpeg_bin,
                "-y",
                "-headers", f"Referer: {embed_url}\r\n",
                "-i", video_url,
                "-headers", f"Referer: {embed_url}\r\n",
                "-i", audio_url,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-metadata", f"title={task.get_display_title()}",
                "-progress", "pipe:1",
                "-nostats",
                str(part_path)
            ]

            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            task._process = proc

            # Read stdout line by line for progress
            last_save = time.time()
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break

                decoded_line = line.decode("utf-8", errors="replace").strip()
                if "=" in decoded_line:
                    k, v = decoded_line.split("=", 1)
                    k = k.strip()
                    v = v.strip()

                    if k in ("out_time_us", "out_time_ms"):
                        microseconds = float(v) if v.replace(".", "", 1).isdigit() else 0
                        current_sec = microseconds / 1_000_000
                        if task.total_duration > 0:
                            task.progress = min(99.5, (current_sec / task.total_duration) * 100.0)
                            # ETA
                            try:
                                speed_val = float(task.speed.replace("x", "")) if task.speed and task.speed != "0x" else 1.0
                                if speed_val > 0.01:
                                    remaining_sec = max(0, (task.total_duration - current_sec) / speed_val)
                                    task.eta = format_time(remaining_sec)
                            except Exception:
                                pass

                    elif k == "speed":
                        task.speed = v

                    elif k == "total_size":
                        if v.isdigit():
                            task.downloaded_size = format_bytes(int(v))

                    elif k == "progress" and v == "end":
                        task.progress = 100.0

                if time.time() - last_save > 2.0:
                    last_save = time.time()
                    self.save_history()

            stderr_output = await proc.stderr.read()
            return_code = await proc.wait()

            if task.status == "cancelled":
                if part_path.exists():
                    part_path.unlink()
                return

            if return_code == 0:
                if part_path.exists():
                    if final_path.exists():
                        final_path.unlink()
                    part_path.rename(final_path)
                    task.downloaded_size = format_bytes(final_path.stat().st_size)

                task.status = "completed"
                task.progress = 100.0
                task.eta = "Fatto"
                task.completed_at = time.time()
            else:
                task.status = "failed"
                task.error_message = stderr_output.decode("utf-8", errors="replace")[-300:] or f"FFmpeg terminato con codice {return_code}"
                if part_path.exists():
                    part_path.unlink()

        except asyncio.CancelledError:
            task.status = "cancelled"
            if task._process:
                try:
                    task._process.terminate()
                except Exception:
                    pass
            if task._part_file and task._part_file.exists():
                task._part_file.unlink()
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            if task._part_file and task._part_file.exists():
                task._part_file.unlink()
        finally:
            task._process = None
            self.save_history()

download_manager = DownloadManager()
