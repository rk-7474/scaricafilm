import os
import re
import json
from pathlib import Path

DEFAULT_CONFIG_PATH = os.environ.get("CONFIG_PATH", "config/settings.json")
DEFAULT_MOVIES_FOLDER = os.environ.get("MOVIES_FOLDER", "/downloads/movies")
DEFAULT_TV_FOLDER = os.environ.get("TV_FOLDER", "/downloads/tv")

DEFAULT_SETTINGS = {
    "streamingcommunity_url": "https://streamingcommunityz.rip",
    "movies_dir": DEFAULT_MOVIES_FOLDER,
    "tv_dir": DEFAULT_TV_FOLDER,
    "preferred_quality": "1080p",   # '1080p', '720p', '480p'
    "preferred_audio": "ita",       # 'ita', 'eng', 'all'
    "max_concurrent_downloads": 2
}

def resolve_storage_path(configured_path: str, default_fallback: str) -> Path:
    if not configured_path or not configured_path.strip():
        configured_path = default_fallback

    clean_p = configured_path.strip().replace('"', '').replace("'", "")

    # Check for Windows drive letter, e.g. C:\Film or c:/Film
    win_match = re.match(r'^([a-zA-Z]):[\\/](.*)$', clean_p)
    if win_match:
        drive_letter = win_match.group(1).lower()
        subpath = win_match.group(2).replace('\\', '/').strip('/')
        # When running inside Docker container and /host_c is mounted
        if os.path.exists(f"/host_{drive_letter}"):
            p = Path(f"/host_{drive_letter}") / subpath
            p.mkdir(parents=True, exist_ok=True)
            return p
        elif os.path.exists("/host_c") and drive_letter == "c":
            p = Path("/host_c") / subpath
            p.mkdir(parents=True, exist_ok=True)
            return p
        # When running outside Docker directly on Windows host
        if os.name == "nt":
            p = Path(f"{drive_letter.upper()}:/{subpath}")
            p.mkdir(parents=True, exist_ok=True)
            return p

    # Standard Linux / container absolute or relative path
    p = Path(clean_p)
    if not p.is_absolute():
        if os.path.exists("/downloads"):
            p = Path(f"/downloads/{clean_p}").resolve()
        else:
            p = Path(clean_p).resolve()

    p.mkdir(parents=True, exist_ok=True)
    return p

def format_display_path(path_str: str) -> str:
    if not path_str:
        return ""
    if path_str.startswith("/host_c/"):
        return "C:\\" + path_str[8:].replace("/", "\\")
    elif path_str.startswith("/host_c"):
        return "C:\\"
    match = re.match(r'^/host_([a-zA-Z])/(.*)$', path_str)
    if match:
        drive = match.group(1).upper()
        return f"{drive}:\\" + match.group(2).replace("/", "\\")
    return path_str

class SettingsManager:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.settings = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            else:
                self.save()

            # Migrate away from legacy jellyfin /media download_dir
            if "download_dir" in self.settings:
                old_dir = self.settings.pop("download_dir", "")
                if "movies_dir" not in self.settings:
                    self.settings["movies_dir"] = DEFAULT_MOVIES_FOLDER
                if "tv_dir" not in self.settings:
                    self.settings["tv_dir"] = DEFAULT_TV_FOLDER
                self.save()

            if not self.settings.get("movies_dir"):
                self.settings["movies_dir"] = DEFAULT_MOVIES_FOLDER
            if not self.settings.get("tv_dir"):
                self.settings["tv_dir"] = DEFAULT_TV_FOLDER

        except Exception as e:
            print(f"[Config] Error loading settings: {e}")

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.config_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            os.replace(tmp_path, self.config_path)
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def update(self, updates: dict):
        self.settings.update(updates)
        # Ensure url does not have trailing slash
        if "streamingcommunity_url" in self.settings:
            self.settings["streamingcommunity_url"] = self.settings["streamingcommunity_url"].rstrip("/")

        if "movies_dir" in self.settings:
            self.settings["movies_dir"] = self.settings["movies_dir"].strip()
        if "tv_dir" in self.settings:
            self.settings["tv_dir"] = self.settings["tv_dir"].strip()

        # Remove legacy download_dir if present
        self.settings.pop("download_dir", None)

        self.save()
        return self.settings

    def get_movies_dir(self) -> Path:
        return resolve_storage_path(self.get("movies_dir", DEFAULT_MOVIES_FOLDER), DEFAULT_MOVIES_FOLDER)

    def get_tv_dir(self) -> Path:
        return resolve_storage_path(self.get("tv_dir", DEFAULT_TV_FOLDER), DEFAULT_TV_FOLDER)

    def get_media_dir(self) -> Path:
        # Backwards compatibility fallback
        return self.get_movies_dir()

    def all(self):
        return dict(self.settings)

settings_manager = SettingsManager()
