#!/bin/bash
set -e

# Always upgrade yt-dlp to the latest version at startup
echo "Upgrading yt-dlp to latest version..."
pip install --upgrade --no-cache-dir yt-dlp

# Show yt-dlp version
echo "yt-dlp version: $(yt-dlp --version)"

# Start the application
echo "Starting TubeAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${TUBEAPI_PORT:-8000}

