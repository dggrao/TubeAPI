#!/bin/bash
set -e

# ── GCS credentials ────────────────────────────────────────────────────────────
# If credentials are passed as a JSON string via environment variable,
# write them to a file so google-auth can pick them up automatically.
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS_JSON" ]; then
    echo "Writing GCS credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON..."
    echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > /app/credentials.json
    export GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
fi

# ── yt-dlp update ──────────────────────────────────────────────────────────────
echo "Upgrading yt-dlp to latest nightly version..."
pip install --upgrade --no-cache-dir yt-dlp[default]
yt-dlp --update-to nightly || echo "Nightly update failed, using pip version"
echo "yt-dlp version: $(yt-dlp --version)"

# ── Start application ──────────────────────────────────────────────────────────
echo "Starting TubeAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${TUBEAPI_PORT:-8000}"
