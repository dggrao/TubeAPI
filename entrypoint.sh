#!/bin/bash
set -e

# Always upgrade yt-dlp to the latest nightly version at startup
# Nightly builds have the latest fixes for YouTube changes
echo "Upgrading yt-dlp to latest nightly version..."
pip install --upgrade --no-cache-dir yt-dlp[default]
yt-dlp --update-to nightly || echo "Nightly update failed, using pip version"

# Show yt-dlp version
echo "yt-dlp version: $(yt-dlp --version)"

# Start the application
echo "Starting TubeAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${TUBEAPI_PORT:-8000}
