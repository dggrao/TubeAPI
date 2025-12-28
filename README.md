# TubeAPI

A self-hosted media download API service powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp). Download videos, audio, and transcripts from YouTube and 1000+ other sites.

## Features

- **Video Download** - Download videos as MP4
- **Audio Download** - Extract audio as MP3
- **Video Info** - Get metadata (title, duration, views, etc.)
- **Transcript** - Extract subtitles/captions as JSON
- **Multi-Site Support** - Works with YouTube, Twitter/X, TikTok, Vimeo, Instagram, Reddit, and [many more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- **Auto-Cleanup** - Automatic file cleanup to save storage
- **Always Updated** - yt-dlp auto-updates on container restart

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tubeapi.git
   cd tubeapi
   ```

2. Create your environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. Start the service:
   ```bash
   docker-compose up -d
   ```

4. Access the API at `http://localhost:8000`

### Using Docker

```bash
docker build -t tubeapi .
docker run -d \
  -p 8000:8000 \
  -e TUBEAPI_USER=admin \
  -e TUBEAPI_PASS=yourpassword \
  --name tubeapi \
  tubeapi
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TUBEAPI_USER` | Basic auth username | `admin` |
| `TUBEAPI_PASS` | Basic auth password | `changeme` |
| `TUBEAPI_PORT` | API port | `8000` |
| `TUBEAPI_TEMP_DIR` | Temp download directory | `/tmp/tubeapi` |
| `TUBEAPI_CLEANUP_MAX_AGE` | Max file age in seconds | `7200` (2 hours) |

## API Endpoints

All endpoints except `/health` require HTTP Basic Authentication.

### Health Check

```
GET /health
```

Returns API status and yt-dlp version. No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "yt_dlp_version": "2024.12.23"
}
```

### Download Video (YouTube)

```
GET /youtube/video?url=<youtube_url>
```

Downloads and returns the video as MP4.

**Example:**
```bash
curl -u admin:password \
  "http://localhost:8000/youtube/video?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -o video.mp4
```

### Download Audio (YouTube)

```
GET /youtube/audio?url=<youtube_url>
```

Extracts and returns audio as MP3.

**Example:**
```bash
curl -u admin:password \
  "http://localhost:8000/youtube/audio?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -o audio.mp3
```

### Get Video Info (YouTube)

```
GET /youtube/info?url=<youtube_url>
```

Returns video metadata as JSON.

**Response:**
```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "description": "...",
  "duration": 212,
  "uploader": "Rick Astley",
  "upload_date": "20091025",
  "view_count": 1500000000,
  "like_count": 15000000,
  "thumbnail": "https://...",
  "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "extractor": "youtube",
  "formats_available": ["1080p", "720p", "480p", "360p"]
}
```

### Get Transcript (YouTube)

```
GET /youtube/transcript?url=<youtube_url>&language=en
```

Returns subtitles/captions as JSON.

**Parameters:**
- `url` (required): YouTube video URL
- `language` (optional): Language code (default: `en`)

**Response:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "language": "en",
  "segments": [
    {
      "start": 0.0,
      "duration": 3.5,
      "text": "We're no strangers to love"
    },
    {
      "start": 3.5,
      "duration": 2.8,
      "text": "You know the rules and so do I"
    }
  ]
}
```

### Download Media (Any Site)

```
GET /media/download?url=<media_url>
```

Downloads media from any yt-dlp supported site.

**Example:**
```bash
# Twitter/X video
curl -u admin:password \
  "http://localhost:8000/media/download?url=https://twitter.com/user/status/123456789" \
  -o video.mp4

# TikTok video
curl -u admin:password \
  "http://localhost:8000/media/download?url=https://www.tiktok.com/@user/video/123456789" \
  -o video.mp4
```

## Coolify Deployment

TubeAPI is designed for easy deployment with Coolify:

1. In Coolify, create a new service from a Git repository
2. Point to your TubeAPI repository
3. Set the build pack to "Docker Compose"
4. Add environment variables in the Coolify dashboard:
   - `TUBEAPI_USER`: Your username
   - `TUBEAPI_PASS`: Your password
5. Deploy!

The health check endpoint (`/health`) is automatically used by Coolify for monitoring.

## Storage Management

TubeAPI uses a two-tier cleanup strategy:

1. **Immediate Cleanup**: Files are deleted immediately after being sent to the client
2. **Scheduled Cleanup**: A background job runs every 30 minutes to remove any orphaned files older than 2 hours

This ensures minimal storage usage on your Raspberry Pi.

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

### API Documentation

When running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT License - feel free to use and modify for your personal projects.

