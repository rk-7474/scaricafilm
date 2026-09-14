import re
import json
import urllib.parse
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from src.config import settings_manager

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

class StreamingCommunityScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _get_base_url(self, base_url: Optional[str] = None) -> str:
        url = base_url or settings_manager.get("streamingcommunity_url", "https://streamingcommunityz.taxi")
        return url.rstrip("/")

    def test_connection(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        target_url = self._get_base_url(base_url)
        try:
            r = self.session.get(target_url, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                return {
                    "ok": True,
                    "status_code": r.status_code,
                    "url": r.url,
                    "message": f"Connessione riuscita a {r.url}"
                }
            return {
                "ok": False,
                "status_code": r.status_code,
                "url": r.url,
                "message": f"Risposta del server: {r.status_code}"
            }
        except Exception as e:
            return {
                "ok": False,
                "status_code": 0,
                "url": target_url,
                "message": f"Errore di connessione: {str(e)}"
            }

    def search_titles(self, query: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        target_url = self._get_base_url(base_url)
        encoded_query = urllib.parse.quote(query.strip())
        search_url = f"{target_url}/it/search?q={encoded_query}"

        r = self.session.get(search_url, timeout=12)
        if r.status_code != 200:
            raise ValueError(f"Ricerca fallita, status code: {r.status_code}")

        soup = BeautifulSoup(r.text, "html.parser")
        app = soup.find(id="app")
        if not app or not app.get("data-page"):
            raise ValueError("Impossibile trovare data-page nei risultati di ricerca")

        data = json.loads(app["data-page"])
        props = data.get("props", {})
        cdn_url = props.get("cdn_url", "https://cdn.streamingcommunityz.taxi").rstrip("/")
        raw_titles = props.get("titles", [])

        results = []
        for t in raw_titles:
            images = t.get("images", [])
            poster_filename = None
            cover_filename = None
            for img in images:
                if img.get("type") == "poster" and not poster_filename:
                    poster_filename = img.get("filename")
                elif img.get("type") == "cover" and not cover_filename:
                    cover_filename = img.get("filename")

            poster_url = f"{cdn_url}/images/{poster_filename}" if poster_filename else (f"{cdn_url}/images/{cover_filename}" if cover_filename else None)

            release_date = t.get("release_date") or t.get("last_air_date") or ""
            year = release_date[:4] if release_date else ""

            results.append({
                "id": t.get("id"),
                "slug": t.get("slug"),
                "name": t.get("name"),
                "type": t.get("type", "movie"), # 'movie' or 'tv'
                "score": t.get("score"),
                "year": year,
                "release_date": release_date,
                "seasons_count": t.get("seasons_count", 0),
                "poster_url": poster_url,
                "plot": t.get("plot", ""),
            })

        return results

    def get_title_details(self, title_id: int, slug: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        target_url = self._get_base_url(base_url)
        detail_url = f"{target_url}/it/titles/{title_id}-{slug}"

        r = self.session.get(detail_url, timeout=12)
        if r.status_code != 200:
            raise ValueError(f"Caricamento dettagli fallito, status code: {r.status_code}")

        soup = BeautifulSoup(r.text, "html.parser")
        app = soup.find(id="app")
        if not app or not app.get("data-page"):
            raise ValueError("Impossibile trovare data-page nei dettagli")

        data = json.loads(app["data-page"])
        props = data.get("props", {})
        title_data = props.get("title", {})
        cdn_url = props.get("cdn_url", "https://cdn.streamingcommunityz.taxi").rstrip("/")

        # Parse poster
        images = title_data.get("images", [])
        poster_filename = None
        for img in images:
            if img.get("type") == "poster":
                poster_filename = img.get("filename")
                break
        poster_url = f"{cdn_url}/images/{poster_filename}" if poster_filename else None

        # Format seasons if TV series
        seasons = []
        for s in title_data.get("seasons", []):
            seasons.append({
                "id": s.get("id"),
                "number": s.get("number"),
                "name": s.get("name") or f"Stagione {s.get('number')}",
                "episodes_count": s.get("episodes_count", 0),
            })

        # Loaded season episodes (usually season 1)
        loaded_season = props.get("loadedSeason") or {}
        first_season_episodes = []
        if loaded_season and "episodes" in loaded_season:
            for ep in loaded_season.get("episodes", []):
                first_season_episodes.append({
                    "id": ep.get("id"),
                    "number": ep.get("number"),
                    "name": ep.get("name") or f"Episodio {ep.get('number')}",
                    "plot": ep.get("plot", ""),
                    "scws_id": ep.get("scws_id")
                })

        return {
            "id": title_data.get("id"),
            "slug": title_data.get("slug"),
            "name": title_data.get("name"),
            "type": title_data.get("type", "movie"),
            "plot": title_data.get("plot", ""),
            "quality": title_data.get("quality", "HD"),
            "runtime": title_data.get("runtime"),
            "score": title_data.get("score"),
            "release_date": title_data.get("release_date") or title_data.get("last_air_date") or "",
            "year": (title_data.get("release_date") or title_data.get("last_air_date") or "")[:4],
            "genres": [g.get("name") for g in title_data.get("genres", []) if isinstance(g, dict)],
            "poster_url": poster_url,
            "seasons": seasons,
            "loaded_season_number": loaded_season.get("number", 1) if loaded_season else 1,
            "episodes": first_season_episodes
        }

    def get_season_episodes(self, title_id: int, slug: str, season_num: int, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        target_url = self._get_base_url(base_url)
        season_url = f"{target_url}/it/titles/{title_id}-{slug}/season-{season_num}"

        r = self.session.get(season_url, timeout=12)
        if r.status_code != 200:
            raise ValueError(f"Caricamento stagione fallito: status code {r.status_code}")

        soup = BeautifulSoup(r.text, "html.parser")
        app = soup.find(id="app")
        if not app or not app.get("data-page"):
            raise ValueError("Impossibile trovare data-page nella pagina stagione")

        data = json.loads(app["data-page"])
        loaded_season = data.get("props", {}).get("loadedSeason", {})
        episodes = []
        for ep in loaded_season.get("episodes", []):
            episodes.append({
                "id": ep.get("id"),
                "number": ep.get("number"),
                "name": ep.get("name") or f"Episodio {ep.get('number')}",
                "plot": ep.get("plot", ""),
                "scws_id": ep.get("scws_id")
            })
        return episodes

    def extract_stream_sources(self, title_id: int, episode_id: Optional[int] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        target_url = self._get_base_url(base_url)
        iframe_endpoint = f"{target_url}/it/iframe/{title_id}"
        if episode_id is not None:
            iframe_endpoint += f"?episode_id={episode_id}"

        r_iframe = self.session.get(iframe_endpoint, headers={"Referer": f"{target_url}/"}, timeout=12)
        if r_iframe.status_code != 200:
            raise ValueError(f"Richiesta iframe fallita: status {r_iframe.status_code}")

        soup = BeautifulSoup(r_iframe.text, "html.parser")
        iframe_tag = soup.find("iframe")
        if not iframe_tag or not iframe_tag.get("src"):
            raise ValueError("Tag iframe non trovato nella risposta")

        embed_url = iframe_tag["src"]

        # 2. Get embed page
        r_embed = self.session.get(embed_url, headers={"Referer": f"{target_url}/"}, timeout=12)
        if r_embed.status_code != 200:
            raise ValueError(f"Richiesta player embed fallita: status {r_embed.status_code}")

        token_match = re.search(r"['\"]token['\"]\s*:\s*['\"]([^'\"]+)['\"]", r_embed.text)
        expires_match = re.search(r"['\"]expires['\"]\s*:\s*['\"]([^'\"]+)['\"]", r_embed.text)
        url_match = re.search(r"window\.masterPlaylist\s*=\s*\{.*?url\s*:\s*['\"]([^'\"]+)['\"]", r_embed.text, re.DOTALL)

        if not (token_match and expires_match and url_match):
            raise ValueError("Parametri masterPlaylist non trovati nella pagina embed")

        token = token_match.group(1)
        expires = expires_match.group(1)
        master_base_url = url_match.group(1)

        # 3. Master playlist URL
        master_playlist_url = f"{master_base_url}?token={token}&expires={expires}&h=1&scz=1&lang=it"

        r_master = self.session.get(
            master_playlist_url,
            headers={"Referer": embed_url, "Origin": "https://vixcloud.co"},
            timeout=12
        )
        if r_master.status_code != 200:
            raise ValueError(f"Master playlist non raggiungibile: status {r_master.status_code}")

        lines = r_master.text.strip().splitlines()

        # Parse audio tracks
        audios = []
        for line in lines:
            if line.startswith("#EXT-X-MEDIA:TYPE=AUDIO"):
                lang_match = re.search(r'LANGUAGE="([^"]+)"', line)
                name_match = re.search(r'NAME="([^"]+)"', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                if uri_match:
                    audios.append({
                        "language": lang_match.group(1) if lang_match else "ita",
                        "name": name_match.group(1) if name_match else "Italian",
                        "url": uri_match.group(1)
                    })

        # Parse subtitle tracks
        subtitles = []
        for line in lines:
            if line.startswith("#EXT-X-MEDIA:TYPE=SUBTITLES"):
                lang_match = re.search(r'LANGUAGE="([^"]+)"', line)
                name_match = re.search(r'NAME="([^"]+)"', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                if uri_match:
                    subtitles.append({
                        "language": lang_match.group(1) if lang_match else "ita",
                        "name": name_match.group(1) if name_match else "Sub",
                        "url": uri_match.group(1)
                    })

        # Parse video streams
        videos = []
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                res_match = re.search(r'RESOLUTION=([0-9x]+)', line)
                bw_match = re.search(r'BANDWIDTH=([0-9]+)', line)
                if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    vid_url = lines[i + 1].strip()
                    rendition = "unknown"
                    rend_match = re.search(r'rendition=([0-9]+p)', vid_url)
                    if rend_match:
                        rendition = rend_match.group(1)
                    elif res_match:
                        rendition = f"{res_match.group(1).split('x')[-1]}p"

                    videos.append({
                        "rendition": rendition,
                        "resolution": res_match.group(1) if res_match else "",
                        "bandwidth": int(bw_match.group(1)) if bw_match else 0,
                        "url": vid_url
                    })

        # Sort videos by bandwidth descending (best first)
        videos.sort(key=lambda x: x["bandwidth"], reverse=True)

        return {
            "embed_url": embed_url,
            "master_playlist_url": master_playlist_url,
            "videos": videos,
            "audios": audios,
            "subtitles": subtitles
        }

scraper = StreamingCommunityScraper()
