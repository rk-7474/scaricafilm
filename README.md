# 🎬 ScaricaFilm - StreamingCommunity WebUI & Downloader

Applicazione web in Python con interfaccia moderna (stile dark mode) per cercare e scaricare film e serie TV da **StreamingCommunity** direttamente nella propria cartella media personale (organizzata per Plex, Jellyfin, Emby, ecc.).

---

## ✨ Caratteristiche Principali

- **Ricerca Diretta su StreamingCommunity**: I titoli provengono direttamente dal catalogo aggiornato di StreamingCommunity (`https://streamingcommunityz.taxi/`), garantendo disponibilità immediata, ID precisi e locandine ad alta risoluzione.
- **Supporto Film e Serie TV**:
  - Film: download con scelta di risoluzione (1080p, 720p, 480p) e lingua audio (Italiano / Inglese).
  - Serie TV: navigazione per stagioni ed episodi, con download di singoli episodi o download in blocco dell'intera stagione.
- **Download Ultra-Veloce con Decrittazione HLS**: Estrazione diretta dei flussi audio/video Master Playlist HLS e muxing automatico con `ffmpeg` in formato `.mp4` (senza bisogno di browser pesanti come Chromium/Playwright a runtime).
- **Monitoraggio Live in Tempo Reale**: Avanzamento %, velocità di download, tempo stimato (ETA) e dimensione file tramite Server-Sent Events (SSE).
- **Organizzazione Automatica Cartelle**:
  - Film: `Movies/{Titolo} ({Anno})/{Titolo} ({Anno}) [{qualità}].mp4`
  - Serie: `TV/{Serie} ({Anno})/Season {SS}/{Serie} - S{SS}E{EE} - {Episodio} [{qualità}].mp4`
- **Impostazioni Flessibili & Persistenti**:
  - Cambio rapido dell'URL di StreamingCommunity dall'interfaccia con pulsante "Test Connessione".
  - Configurazione cartella di destinazione media, qualità preferita e lingua audio.
- **Immagine Docker Ultra-Leggera**: Basata su `python:3.12-alpine` con `ffmpeg` nativo (~90 MB totali, ideale per NAS, server domestici e Raspberry Pi).

---

## 🚀 Avvio Rapido con Docker Compose (Consigliato)

1. Avvia il container in background:
```bash
docker compose up -d
```

2. Apri il browser all'indirizzo:
```
http://localhost:8000
```

3. I file scaricati verranno salvati nella cartella locale `./downloads` (mappata nel container come `/media`). Le impostazioni e la cronologia saranno salvate in `./config`.

---

## 💻 Esecuzione Locale (Senza Docker)

Requisiti: Python >= 3.10 e `ffmpeg` installato nel sistema.

### Con `uv` (consigliato):
```bash
# Sincronizza le dipendenze
uv sync

# Avvia l'applicazione
uv run python src/main.py
```

### Con `pip` standard:
```bash
# Crea un virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Installa le dipendenze
pip install -r requirements.txt

# Avvia il server
python src/main.py
```

Apri `http://localhost:8000` nel browser.

---

## ⚙️ Configurazione & Variabili d'Ambiente

| Variabile | Valore Predefinito | Descrizione |
|---|---|---|
| `MEDIA_FOLDER` | `/media` (o `./downloads`) | Percorso della cartella principale in cui salvare i download |
| `CONFIG_PATH` | `/app/config/settings.json` | Percorso del file di impostazioni persistenti |
| `PORT` | `8000` | Porta HTTP del server WebUI |
| `HOST` | `0.0.0.0` | Indirizzo di binding del server |
| `TZ` | `Europe/Rome` | Fuso orario del container |

---

## 🛠️ Struttura del Progetto

```
scaricafilm/
├── Dockerfile                  # Immagine Alpine ultra-leggera con FFmpeg
├── docker-compose.yml          # Configurazione container e volumi
├── requirements.txt            # Dipendenze essenziali
├── pyproject.toml              # Specifiche progetto uv/pip
├── README.md                   # Documentazione
├── config/                     # File di configurazione persistenti (settings.json, downloads_history.json)
├── downloads/                  # Cartella di download predefinita
└── src/
    ├── main.py                 # Entrypoint server (uvicorn)
    ├── app.py                  # API FastAPI e gestione routing
    ├── config.py               # Gestione impostazioni e persistenza JSON
    ├── scraper.py              # Ricerca, estrazione metadati e HLS da StreamingCommunity
    ├── downloader.py           # Gestore code, esecuzione ffmpeg e calcolo progresso
    ├── templates/
    │   └── index.html          # Interfaccia WebUI HTML5
    └── static/
        ├── css/style.css       # Stili moderni Dark Mode
        └── js/app.js           # Logica client e monitor SSE
```
