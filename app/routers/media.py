import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import verify_credentials
from app.models.schemas import MediaRequest
from app.services.downloader import download_media, sanitize_filename

router = APIRouter()


def cleanup_file(file_path: Path):
    """Background task to clean up downloaded files."""
    try:
        # Delete the file
        if file_path.exists():
            file_path.unlink()
        # Delete the parent directory if empty
        parent = file_path.parent
        if parent.exists() and not any(parent.iterdir()):
            shutil.rmtree(parent, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors


# Media type mapping for content-type headers
MEDIA_TYPE_MAP = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}


@router.post("/download")
async def download(
    request: MediaRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download media from any yt-dlp supported site.
    
    Request body:
    - url: Media URL (supports 1000+ sites via yt-dlp)
    
    Supports YouTube, Twitter/X, TikTok, Vimeo, Instagram, Reddit,
    and many more. See https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
    
    Returns the media file as a binary stream.
    """
    try:
        file_path, title, media_type = download_media(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Schedule cleanup after response is sent
    background_tasks.add_task(cleanup_file, file_path)

    # Determine content type and filename
    extension = file_path.suffix.lower()
    content_type = MEDIA_TYPE_MAP.get(extension, "application/octet-stream")
    safe_filename = sanitize_filename(title) + extension

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )
