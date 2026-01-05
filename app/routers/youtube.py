import logging
import shutil
from pathlib import Path
import yt_dlp

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import verify_credentials
from app.models.schemas import (
    VideoInfo,
    VideoRequest,
)
from app.services.downloader import download_video, sanitize_filename

logger = logging.getLogger(__name__)

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
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}") 


import random
import string

from app.services.storage import upload_file


@router.post("/video")
async def get_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download a YouTube video as MP4 and upload to Supabase.
    
    Request body:
    - url: YouTube video URL
    - quality: Video quality (e.g., "1080", "720", "480", "best"). Default: "1080"
    
    Returns:
    - JSON object containing the public URL of the uploaded file.
    """
    logger.info(f"Received download request for URL: {request.url} (Quality: {request.quality})")
    
    try:
        file_path, title = download_video(
            request.url, 
            quality=request.quality or "1080",
            proxy=request.proxy
        )
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"yt-dlp download error: {error_msg}")
        
        # Check for common client-side errors
        client_errors = [
            "Video unavailable",
            "Private video",
            "Sign in to confirm your age",
            "This video has been removed",
            "Incomplete YouTube ID",
            "KeyError"
        ]
        
        if any(err in error_msg for err in client_errors):
            raise HTTPException(status_code=400, detail=f"Video unavailable or invalid: {error_msg}")
            
        raise HTTPException(status_code=400, detail=f"Download failed: {error_msg}")
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during video download")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    try:
        # Generate random 16-char alphanumeric string for filename
        # 16digit randomly generated uuid string without special charters
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        extension = file_path.suffix.lower()
        safe_filename = f"{random_string}{extension}"
        
        # Upload to Supabase
        public_url = upload_file(file_path, safe_filename)
        
    except Exception as e:
        # Clean up local file if upload fails
        cleanup_file(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # Schedule cleanup for local file
    background_tasks.add_task(cleanup_file, file_path)

    return {
        "status": "success",
        "url": public_url,
        "title": title,
        "media_type": "video/mp4",
        "filename": safe_filename
    }



