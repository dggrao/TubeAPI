import re
import shutil
import uuid
from pathlib import Path

import yt_dlp

from app.config import settings
from app.services.downloader import BASE_YDL_OPTS


def parse_vtt_content(content: str) -> list[dict]:
    """
    Parse VTT subtitle content into segments.
    
    Args:
        content: VTT file content
        
    Returns:
        List of transcript segments with start, duration, and text
    """
    segments = []
    
    # Split by double newlines to get cue blocks
    blocks = re.split(r'\n\n+', content)
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
            
        # Look for timestamp line (e.g., "00:00:01.000 --> 00:00:04.000")
        timestamp_pattern = r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})'
        
        for i, line in enumerate(lines):
            match = re.match(timestamp_pattern, line)
            if match:
                start_str, end_str = match.groups()
                
                # Parse timestamps to seconds
                start = parse_timestamp(start_str)
                end = parse_timestamp(end_str)
                duration = end - start
                
                # Get text from remaining lines
                text_lines = lines[i + 1:]
                text = ' '.join(text_lines).strip()
                
                # Clean up VTT formatting tags
                text = re.sub(r'<[^>]+>', '', text)
                text = text.strip()
                
                if text:
                    segments.append({
                        "start": round(start, 3),
                        "duration": round(duration, 3),
                        "text": text,
                    })
                break
    
    return segments


def parse_timestamp(timestamp: str) -> float:
    """
    Parse VTT timestamp to seconds.
    
    Args:
        timestamp: Timestamp string (HH:MM:SS.mmm or HH:MM:SS,mmm)
        
    Returns:
        Time in seconds
    """
    # Replace comma with period for consistency
    timestamp = timestamp.replace(',', '.')
    
    parts = timestamp.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(timestamp)


def get_transcript(url: str, language: str = "en") -> dict:
    """
    Extract transcript/subtitles from a video.
    
    Args:
        url: Video URL
        language: Preferred subtitle language (default: en)
        
    Returns:
        Dictionary containing video_id, title, language, and segments
    """
    output_dir = settings.ensure_temp_dir()
    download_id = str(uuid.uuid4())
    download_dir = output_dir / download_id
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / "%(id)s")

    ydl_opts = {
        **BASE_YDL_OPTS,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [language, f"{language}.*"],
        "subtitlesformat": "vtt",
        "outtmpl": output_template,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not info:
        raise ValueError("Could not extract video information")

    video_id = info.get("id", "")
    title = info.get("title", "Unknown")

    # Find the subtitle file
    subtitle_file = None
    actual_language = language
    
    for file in download_dir.iterdir():
        if file.suffix == ".vtt":
            subtitle_file = file
            # Extract language from filename if present
            name_parts = file.stem.split(".")
            if len(name_parts) > 1:
                actual_language = name_parts[-1]
            break

    if not subtitle_file:
        # Clean up directory
        shutil.rmtree(download_dir, ignore_errors=True)
        raise ValueError(f"No subtitles available for language: {language}")

    # Read and parse the subtitle file
    content = subtitle_file.read_text(encoding="utf-8")
    segments = parse_vtt_content(content)

    # Clean up directory
    shutil.rmtree(download_dir, ignore_errors=True)

    return {
        "video_id": video_id,
        "title": title,
        "language": actual_language,
        "segments": segments,
    }
