import re
import uuid
from pathlib import Path
from typing import Optional

import yt_dlp

from app.config import settings


# Base yt-dlp options for network reliability on Raspberry Pi / home networks
# These settings help handle temporary network drops, IPv6 issues, and rate limiting
BASE_YDL_OPTS = {
    # Force IPv4 to avoid IPv6 connectivity issues
    "force_ipv4": True,
    # Retry settings for network reliability
    "retries": 10,
    "fragment_retries": 10,
    "file_access_retries": 5,
    "extractor_retries": 5,
    # Socket timeout (seconds)
    "socket_timeout": 30,
    # Rate limiting to avoid 429 Too Many Requests errors
    "sleep_interval": 1,  # Sleep 1 second between requests
    "max_sleep_interval": 5,  # Maximum sleep interval
    "sleep_interval_requests": 1,  # Sleep between HTTP requests
    "sleep_interval_subtitles": 2,  # Sleep before subtitle downloads
    # Continue on download errors
    "ignoreerrors": False,
    # Logging settings - Enable output to see ffmpeg progress
    "quiet": False,
    "no_warnings": False,
    "verbose": True,
}


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize filename to remove invalid characters and limit length.
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename (default: 100)
        
    Returns:
        Sanitized filename safe for all filesystems
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    # Replace special Unicode characters that might cause issues
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    # Replace multiple spaces/underscores with single
    filename = re.sub(r'[\s_]+', '_', filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # Limit length (leave room for extension)
    filename = filename[:max_length]
    # Final cleanup
    filename = filename.strip('._')
    return filename if filename else "download"


def get_quality_format(quality: str) -> str:
    """
    Convert quality string to yt-dlp format selector.
    
    Args:
        quality: Quality string like "1080", "720", "480", "360", "best", "worst"
        
    Returns:
        yt-dlp format selector string
    """
    quality = quality.lower().strip()
    
    # Remove 'p' suffix if present (e.g., "1080p" -> "1080")
    quality = quality.rstrip('p')
    
    if quality == "best":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    elif quality == "worst":
        return "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst"
    elif quality.isdigit():
        height = int(quality)
        # Select best video up to specified height, with audio
        return f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[height<={height}]/best"
    else:
        # Default to 1080p or less
        return "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]/best"


def get_video_info(url: str) -> dict:
    """
    Extract video information without downloading.
    
    Args:
        url: Video URL
        
    Returns:
        Dictionary containing video metadata
    """
    ydl_opts = {
        **BASE_YDL_OPTS,
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


def download_video(
    url: str,
    quality: str = "1080",
    output_dir: Optional[Path] = None
) -> tuple[Path, str]:
    """
    Download video as MP4.
    
    Args:
        url: Video URL
        quality: Video quality (e.g., "1080", "720", "480", "best")
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

    # Use UUID-based filename to avoid filesystem issues
    output_file = download_dir / f"{download_id}.%(ext)s"

    format_selector = get_quality_format(quality)

    ydl_opts = {
        **BASE_YDL_OPTS,
        "format": format_selector,
        "outtmpl": str(output_file),
        "merge_output_format": "mp4",
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

    # Use UUID-based filename to avoid filesystem issues
    output_file = download_dir / f"{download_id}.%(ext)s"

    ydl_opts = {
        **BASE_YDL_OPTS,
        "format": "bestaudio/best",
        "outtmpl": str(output_file),
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

    # Use UUID-based filename to avoid filesystem issues
    output_file = download_dir / f"{download_id}.%(ext)s"

    ydl_opts = {
        **BASE_YDL_OPTS,
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "outtmpl": str(output_file),
        "merge_output_format": "mp4",
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
