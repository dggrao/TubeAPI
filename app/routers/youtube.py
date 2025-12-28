import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.auth import verify_credentials
from app.models.schemas import VideoInfo, TranscriptResponse
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


@router.get("/video")
async def get_video(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube video URL"),
    username: str = Depends(verify_credentials),
):
    """
    Download a YouTube video as MP4.
    
    Returns the video file as a binary stream.
    """
    try:
        file_path, title = download_video(url)
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


@router.get("/audio")
async def get_audio(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube video URL"),
    username: str = Depends(verify_credentials),
):
    """
    Download audio from a YouTube video as MP3.
    
    Returns the audio file as a binary stream.
    """
    try:
        file_path, title = download_audio(url)
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


@router.get("/info", response_model=VideoInfo)
async def get_info(
    url: str = Query(..., description="YouTube video URL"),
    username: str = Depends(verify_credentials),
):
    """
    Get metadata for a YouTube video.
    
    Returns video information including title, duration, view count, etc.
    """
    try:
        info = get_video_info(url)
        return VideoInfo(**info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get info: {str(e)}")


@router.get("/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    url: str = Query(..., description="YouTube video URL"),
    language: str = Query("en", description="Subtitle language code"),
    username: str = Depends(verify_credentials),
):
    """
    Get transcript/subtitles for a YouTube video.
    
    Returns the transcript as a list of timed segments.
    """
    try:
        transcript = get_transcript(url, language)
        return TranscriptResponse(**transcript)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

