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
        self.save()
        return self.settings

    def all(self):
        return dict(self.settings)

settings_manager = SettingsManager()
