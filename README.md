# TubeAPI

A self-hosted media download API service powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp). Download videos, audio, and transcripts from YouTube and 1000+ other sites.

## Features

- **Video Download** - Download videos as MP4 with selectable quality
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
| `SUPABASE_URL` | Supabase Project URL | - |
| `SUPABASE_KEY` | Supabase Anon/Service Key | - |
| `SUPABASE_BUCKET` | Storage Bucket Name | `yt-stock` |

## API Endpoints

All endpoints except `/health` require HTTP Basic Authentication. All download/info endpoints use POST with JSON body.

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
POST /youtube/video
```

Downloads video as MP4 and uploads to Supabase. Returns a public URL.

**Request Body:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "1080"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | YouTube video URL |
| `quality` | string | No | Video quality: "1080", "720", "480", "360", "best", "worst". Default: "1080" |

**Example:**

```bash
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "720"}' \
  "http://localhost:8000/youtube/video"

# Returns JSON with public URL:
# {
#   "status": "success",
#   "url": "https://your-project.supabase.co/storage/v1/object/public/yt-stock/abc123def456ghi7.mp4",
#   "title": "Video Title",
#   "media_type": "video/mp4",
#   "filename": "abc123def456ghi7.mp4"
# }
```

### Download Audio (YouTube)

```
POST /youtube/audio
```

Extracts and returns audio as MP3.

**Request Body:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Example:**

```bash
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  "http://localhost:8000/youtube/audio" \
  -o audio.mp3
```

### Get Video Info (YouTube)

```
POST /youtube/info
```

Returns video metadata as JSON.

**Request Body:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Example:**

```bash
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  "http://localhost:8000/youtube/info"
```

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
POST /youtube/transcript
```

Returns subtitles/captions as JSON.

**Request Body:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "language": "es"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | YouTube video URL |
| `language` | string | No | Language code. If omitted, uses smart fallback (see below) |

**Smart Subtitle Fallback (when language is not specified):**

1. Original language subtitles (uploaded by creator)
2. English subtitles
3. Auto-generated English

**When language IS specified:**

1. Original subtitles for that language
2. Auto-generated subtitles for that language
3. Falls back to default priority

**Example (smart fallback - no language):**

```bash
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  "http://localhost:8000/youtube/transcript"
```

**Example (specific language):**

```bash
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "language": "es"}' \
  "http://localhost:8000/youtube/transcript"
```

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
POST /media/download
```

Downloads media from any yt-dlp supported site and uploads it to Supabase. Returns a public URL.

**Request Body:**

```json
{
  "url": "https://twitter.com/user/status/123456789"
}
```

**Example:**

```bash
# Twitter/X video
curl -u admin:pass \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://twitter.com/user/status/123456789"}' \
  "http://localhost:8000/media/download"

# Returns JSON with public URL:
# {
#   "status": "success",
#   "url": "https://your-project.supabase.co/storage/v1/object/public/yt-stock/Video_Title.mp4",
#   "title": "Video Title",
#   "media_type": "video/mp4",
#   "filename": "Video_Title.mp4"
# }
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
