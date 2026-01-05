# TubeAPI

A FastAPI service for downloading YouTube videos using `yt-dlp` and uploading them to Supabase Storage.

## Features

- 🚀 Fast and async API using FastAPI
- 📹 Powered by `yt-dlp` (Nightly Build)
- ☁️ Auto-upload to Supabase Storage
- 🔐 Basic Authentication
- 🧹 Auto-cleanup of temporary files

## Usage

### 1. Check Health

Verify the service is running and see the current `yt-dlp` version.

```bash
curl -s http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "yt_dlp_version": "2024.12.23.232938"
}
```

### 2. Download Video

Download a video by providing its URL.

**Basic Auth:**
- User: `admin` (default)
- Password: `changeme` (default)

**Command:**
```bash
curl -v -u admin:changeme -X POST "http://localhost:8000/youtube/video" \
   -H "Content-Type: application/json" \
   -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "1080"}'
```

**Parameters:**
- `url`: The YouTube video URL (Required)
- `quality`: Target quality (e.g., "1080", "720", "best"). Defaults to "1080".
- `proxy`: Optional proxy URL.

**Response:**
```json
{
  "status": "success",
  "url": "https://your-project.supabase.co/...",
  "title": "Rick Astley - Never Gonna Give You Up",
  "media_type": "video/mp4",
  "filename": "a1b2c3d4e5f6g7h8.mp4"
}
```

## Setup

1. **Clone & Build:**
   ```bash
   docker-compose up -d --build
   ```

2. **Environment Variables:**
   Create a `.env` file based on `.env.example` to configure Supabase credentials.
