import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.auth import verify_credentials
from app.models.schemas import MediaRequest
from app.services.downloader import download_media, sanitize_filename
from app.services.storage import upload_file

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


@router.post("/download")
async def download(
    request: MediaRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials),
):
    """
    Download media from any yt-dlp supported site and upload to Supabase.
    
    Request body:
    - url: Media URL (supports 1000+ sites via yt-dlp)
    
    Returns:
    - JSON object containing the public URL of the uploaded file.
    """
    try:
        file_path, title, media_type = download_media(request.url, proxy=request.proxy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    try:
        # Determine filename
        extension = file_path.suffix.lower()
        safe_filename = sanitize_filename(title) + extension
        
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
        "media_type": media_type,
        "filename": safe_filename
    }
