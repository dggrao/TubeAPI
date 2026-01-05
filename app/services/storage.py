import logging
from pathlib import Path
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

def upload_file(file_path: Path, filename: str = None) -> str:
    """
    Upload a file to Supabase storage and return the public URL.
    
    Args:
        file_path: Path to the local file
        filename: Optional filename to use in storage. If not provided, uses file_path.name
        
    Returns:
        Public URL of the uploaded file
    """
    if not filename:
        filename = file_path.name
        
    # Construct the upload URL
    # URL format: {supabase_url}/storage/v1/object/{bucket}/{filename}
    # We'll use a 'public' folder inside the bucket to keep it organized if needed, 
    # or just root. The prompt example showed 'yt-stock/folder/avatar1.png'.
    # Let's put it in a 'videos' folder for better organization or just root?
    # User said: "It's a public bucket... upload the file to it... response with a public link"
    # User example: https://supabase.dynoxglobal.com/storage/v1/object/yt-stock/folder/avatar1.png
    
    # Check if Supabase credentials are set
    if not settings.supabase_url or not settings.supabase_key:
        logger.warning(f"Supabase credentials not set. Skipping upload for {filename}.")
        return f"http://localhost:8000/skipped-upload/{filename}"

    bucket = settings.supabase_bucket
    key = filename
    
    upload_url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{key}"
    
    headers = {
        "Authorization": f"Bearer {settings.supabase_key}",
        # content-type is set automatically by httpx when using files, but we can be explicit if needed.
        # However, the user example showed raw data binary upload or multipart.
        # curl -X POST ... --data-binary @...
        # Let's use data-binary equivalent for simple upload if possible, or multipart.
        # Supabase API usually accepts raw body for simple uploads.
    }
    
    # MIME type detection
    content_type = "application/octet-stream"
    import mimetypes
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        content_type = mime
        
    headers["Content-Type"] = content_type
    
    with open(file_path, "rb") as f:
        file_content = f.read()
        
    response = httpx.post(
        upload_url,
        headers=headers,
        content=file_content,
        timeout=300.0  # Large timeout for video files
    )
    
    if response.status_code not in [200, 201]:
        # If file already exists, it might return 400 or error.
        # We should use upsert maybe? 
        # User said: "objects table permissions: only insert when you are uploading new files and select, insert, and update when you are upserting files."
        # If we just POST, it's an insert.
        # If we want to overwrite, we might need x-upsert header.
        # Let's just try insert first. UUID filenames make collisions unlikely.
        raise Exception(f"Failed to upload to Supabase: {response.status_code} - {response.text}")
        
    # Construct Public URL
    # https://supabase.dynoxglobal.com/storage/v1/object/public/yt-stock/folder/avatar1.png
    public_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{key}"
    
    return public_url
