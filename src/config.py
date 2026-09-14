import os
import json
from pathlib import Path

DEFAULT_CONFIG_PATH = os.environ.get("CONFIG_PATH", "config/settings.json")
DEFAULT_MEDIA_FOLDER = os.environ.get("MEDIA_FOLDER", os.path.abspath("downloads"))

DEFAULT_SETTINGS = {
    "streamingcommunity_url": "https://streamingcommunityz.taxi",
    "download_dir": DEFAULT_MEDIA_FOLDER,
    "preferred_quality": "1080p",   # '1080p', '720p', '480p'
    "preferred_audio": "ita",       # 'ita', 'eng', 'all'
    "max_concurrent_downloads": 2
}

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

            # Ensure valid download_dir inside Docker
            env_media = os.environ.get("MEDIA_FOLDER")
            if env_media:
                current_dir = self.settings.get("download_dir", "")
                # If running inside Docker and dir is a host-specific path or doesn't exist
                if not current_dir or current_dir.startswith("/home/") or not os.path.exists(current_dir):
                    self.settings["download_dir"] = env_media
                    self.save()
        except Exception as e:
            print(f"[Config] Error loading settings: {e}")

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
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

        # If running inside Docker, validate download_dir
        env_media = os.environ.get("MEDIA_FOLDER")
        if env_media:
            dl = self.settings.get("download_dir", "")
            if not dl or dl.startswith("/home/") or not os.path.exists(dl):
                self.settings["download_dir"] = env_media

        self.save()
        return self.settings

    def get_media_dir(self) -> Path:
        env_media = os.environ.get("MEDIA_FOLDER")
        dl = self.settings.get("download_dir", "")
        if env_media:
            if not dl or dl.startswith("/home/") or not os.path.exists(dl):
                p = Path(env_media)
            else:
                p = Path(dl)
            p.mkdir(parents=True, exist_ok=True)
            return p

        if not dl:
            p = Path(os.path.abspath("downloads"))
        else:
            p = Path(dl)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def all(self):
        return dict(self.settings)

settings_manager = SettingsManager()
