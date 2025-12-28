import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import verify_credentials
from app.models.schemas import (
    VideoInfo,
    TranscriptResponse,
    VideoRequest,
    AudioRequest,
    InfoRequest,
    TranscriptRequest,
)
from app.services.downloader import get_video_info, download_video, download_audio, sanitize_filename
from app.services.transcript import get_transcript

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


@router.post("/video")
async def get_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download a YouTube video as MP4.
    
    Request body:
    - url: YouTube video URL
    - quality: Video quality (e.g., "1080", "720", "480", "best"). Default: "1080"
    
    Returns the video file as a binary stream.
    """
    try:
        file_path, title = download_video(request.url, quality=request.quality or "1080")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Schedule cleanup after response is sent
    background_tasks.add_task(cleanup_file, file_path)

    safe_filename = sanitize_filename(title) + ".mp4"

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )


@router.post("/audio")
async def get_audio(
    request: AudioRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download audio from a YouTube video as MP3.
    
    Request body:
    - url: YouTube video URL
    
    Returns the audio file as a binary stream.
    """
    try:
        file_path, title = download_audio(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Schedule cleanup after response is sent
    background_tasks.add_task(cleanup_file, file_path)

    safe_filename = sanitize_filename(title) + ".mp3"

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )


@router.post("/info", response_model=VideoInfo)
async def get_info(
    request: InfoRequest,
    username: str = Depends(verify_credentials),
):
    """
    Get metadata for a YouTube video.
    
    Request body:
    - url: YouTube video URL
    
    Returns video information including title, duration, view count, etc.
    """
    try:
        info = get_video_info(request.url)
        return VideoInfo(**info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get info: {str(e)}")


@router.post("/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    request: TranscriptRequest,
    username: str = Depends(verify_credentials),
):
    """
    Get transcript/subtitles for a YouTube video.
    
    Request body:
    - url: YouTube video URL
    - language: Subtitle language code (optional)
    
    Subtitle priority when language is NOT specified:
    1. Original language subtitles
    2. English subtitles
    3. Auto-generated English
    
    When language IS specified:
    1. Original subtitles for that language
    2. Auto-generated for that language
    3. Falls back to default priority
    
    Returns the transcript as a list of timed segments.
    """
    try:
        transcript = get_transcript(request.url, request.language)
        return TranscriptResponse(**transcript)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")
