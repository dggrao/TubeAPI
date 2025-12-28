import os
import re
import uuid
from pathlib import Path
from typing import Optional

import yt_dlp

from app.config import settings


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Trim and limit length
    filename = filename.strip()[:200]
    return filename if filename else "download"


def get_video_info(url: str) -> dict:
    """
    Extract video information without downloading.
    
    Args:
        url: Video URL
        
    Returns:
        Dictionary containing video metadata
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Could not extract video information")

    # Extract available format descriptions
    formats_available = []
    if info.get("formats"):
        for fmt in info["formats"]:
            if fmt.get("format_note"):
                formats_available.append(fmt["format_note"])
        formats_available = list(set(formats_available))

    return {
        "id": info.get("id", ""),
        "title": info.get("title", "Unknown"),
        "description": info.get("description"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "uploader_id": info.get("uploader_id"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "thumbnail": info.get("thumbnail"),
        "webpage_url": info.get("webpage_url", url),
        "extractor": info.get("extractor", "unknown"),
        "formats_available": formats_available,
    }


def download_video(url: str, output_dir: Optional[Path] = None) -> tuple[Path, str]:
    """
    Download video as MP4.
    
    Args:
        url: Video URL
        output_dir: Directory to save the file (defaults to temp dir)
        
    Returns:
        Tuple of (file_path, title)
    """
    if output_dir is None:
        output_dir = settings.ensure_temp_dir()

    # Create unique subdirectory for this download
    download_id = str(uuid.uuid4())
    download_dir = output_dir / download_id
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not info:
        raise ValueError("Could not download video")

    title = info.get("title", "video")
    
    # Find the downloaded file
    for file in download_dir.iterdir():
        if file.is_file() and file.suffix == ".mp4":
            return file, title

    # If no mp4 found, look for any video file
    for file in download_dir.iterdir():
        if file.is_file():
            return file, title

    raise FileNotFoundError("Downloaded file not found")


def download_audio(url: str, output_dir: Optional[Path] = None) -> tuple[Path, str]:
    """
    Download audio as MP3.
    
    Args:
        url: Video URL
        output_dir: Directory to save the file (defaults to temp dir)
        
    Returns:
        Tuple of (file_path, title)
    """
    if output_dir is None:
        output_dir = settings.ensure_temp_dir()

    # Create unique subdirectory for this download
    download_id = str(uuid.uuid4())
    download_dir = output_dir / download_id
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not info:
        raise ValueError("Could not download audio")

    title = info.get("title", "audio")
    
    # Find the downloaded file
    for file in download_dir.iterdir():
        if file.is_file() and file.suffix == ".mp3":
            return file, title

    # If no mp3 found, look for any audio file
    for file in download_dir.iterdir():
        if file.is_file():
            return file, title

    raise FileNotFoundError("Downloaded file not found")


def download_media(url: str, output_dir: Optional[Path] = None) -> tuple[Path, str, str]:
    """
    Download media from any yt-dlp supported site.
    
    Args:
        url: Media URL
        output_dir: Directory to save the file (defaults to temp dir)
        
    Returns:
        Tuple of (file_path, title, media_type)
    """
    if output_dir is None:
        output_dir = settings.ensure_temp_dir()

    # Create unique subdirectory for this download
    download_id = str(uuid.uuid4())
    download_dir = output_dir / download_id
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not info:
        raise ValueError("Could not download media")

    title = info.get("title", "media")
    
    # Find the downloaded file
    for file in download_dir.iterdir():
        if file.is_file():
            # Determine media type from extension
            ext = file.suffix.lower()
            if ext in [".mp4", ".webm", ".mkv", ".avi", ".mov"]:
                media_type = "video"
            elif ext in [".mp3", ".m4a", ".wav", ".flac", ".ogg"]:
                media_type = "audio"
            else:
                media_type = "unknown"
            return file, title, media_type

    raise FileNotFoundError("Downloaded file not found")

