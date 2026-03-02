import logging
import random
import shutil
import string
from pathlib import Path

import yt_dlp
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth import verify_credentials
from app.models.schemas import VideoRequest
from app.services.cleanup import schedule_gcs_deletion
from app.services.downloader import download_video
from app.services.storage import upload_file

logger = logging.getLogger(__name__)

router = APIRouter()


def _cleanup_file(file_path: Path):
    """Background task: delete local downloaded file and its parent dir if empty."""
    try:
        if file_path.exists():
            file_path.unlink()
        parent = file_path.parent
        if parent.exists() and not any(parent.iterdir()):
            shutil.rmtree(parent, ignore_errors=True)
    except Exception as exc:
        logger.error("Error cleaning up local file %s: %s", file_path, exc)


@router.post("/video")
async def get_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download a YouTube video as MP4, upload to GCS, and return a signed URL.

    The URL is valid for 1 hour, after which the file is also deleted from GCS.

    Request body:
    - url:     YouTube video URL
    - quality: Video quality ("1080", "720", "480", "best"). Default: "1080"
    - proxy:   Optional proxy URL

    Returns:
    - JSON with a signed GCS URL valid for 1 hour.
    """
    logger.info("Download request: url=%s quality=%s", request.url, request.quality)

    # --- Download ---
    try:
        file_path, title = download_video(
            request.url,
            quality=request.quality or "1080",
            proxy=request.proxy,
        )
    except yt_dlp.utils.DownloadError as exc:
        error_msg = str(exc)
        logger.error("yt-dlp error: %s", error_msg)
        client_errors = [
            "Video unavailable", "Private video", "Sign in to confirm your age",
            "This video has been removed", "Incomplete YouTube ID", "KeyError",
        ]
        status = 400 if any(e in error_msg for e in client_errors) else 400
        raise HTTPException(status_code=status, detail=f"Download failed: {error_msg}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during video download")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")

    # --- Upload to GCS ---
    try:
        random_string = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
        safe_filename = f"{random_string}{file_path.suffix.lower()}"

        signed_url, gcs_filename = upload_file(file_path, safe_filename)
    except Exception as exc:
        background_tasks.add_task(_cleanup_file, file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    # Clean up local file and schedule GCS deletion after 1 hour
    background_tasks.add_task(_cleanup_file, file_path)
    schedule_gcs_deletion(gcs_filename)

    return {
        "status": "success",
        "url": signed_url,
        "title": title,
        "media_type": "video/mp4",
        "filename": gcs_filename,
    }
