import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth import verify_credentials
from app.models.schemas import MediaRequest
from app.services.cleanup import schedule_gcs_deletion
from app.services.downloader import download_media, sanitize_filename
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
    except Exception:
        pass


@router.post("/download")
async def download(
    request: MediaRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download media from any yt-dlp supported site, upload to GCS, return a signed URL.

    The URL is valid for 1 hour, after which the file is also deleted from GCS.

    Request body:
    - url:   Media URL (1000+ sites supported by yt-dlp)
    - proxy: Optional proxy URL

    Returns:
    - JSON with a signed GCS URL valid for 1 hour.
    """
    # --- Download ---
    try:
        file_path, title, media_type = download_media(request.url, proxy=request.proxy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}")

    # --- Upload to GCS ---
    try:
        safe_filename = sanitize_filename(title) + file_path.suffix.lower()
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
        "media_type": media_type,
        "filename": gcs_filename,
    }
