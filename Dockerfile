# Use an ultra-lightweight Python Alpine base
FROM python:3.12-alpine

# Install FFmpeg and essential runtime certificates/tzdata
RUN apk add --no-cache ffmpeg ca-certificates tzdata

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Create downloads and configuration directories
RUN mkdir -p /downloads /media /app/config

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    MOVIES_FOLDER=/downloads/movies \
    TV_FOLDER=/downloads/tv \
    CONFIG_PATH=/app/config/settings.json

EXPOSE 8000

# Run FastAPI app with Uvicorn
CMD ["python", "-m", "src.main"]
