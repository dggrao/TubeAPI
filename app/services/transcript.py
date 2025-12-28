import re
import shutil
import uuid
from pathlib import Path

import yt_dlp

from app.config import settings
from app.services.downloader import BASE_YDL_OPTS


def parse_srt_content(content: str) -> list[dict]:
    """
    Parse SRT subtitle content into segments.
    
    Args:
        content: SRT file content
        
    Returns:
        List of transcript segments with start, duration, and text
    """
    segments = []
    
    # SRT format: index, timestamp line, text, blank line
    # Split by double newlines to get cue blocks
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        
        # Skip the index line (first line is just a number)
        # Look for timestamp line (e.g., "00:00:01,000 --> 00:00:04,000")
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
                
                # Clean up formatting tags
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\{[^}]+\}', '', text)  # Remove ASS/SSA tags
                text = text.strip()
                
                if text:
                    segments.append({
                        "start": round(start, 3),
                        "duration": round(duration, 3),
                        "text": text,
                    })
                break
    
    return segments


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
    Parse SRT/VTT timestamp to seconds.
    
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


def get_transcript(url: str, language: str | None = None) -> dict:
    """
    Extract transcript/subtitles from a video.
    
    Uses SRT format by default as it has higher success rate and avoids 429 errors.
    
    Subtitle priority:
    - If no language specified: original language -> English -> auto-generated English
    - If language specified: original of that lang -> auto-generated of that lang -> fallback to default
    
    Args:
        url: Video URL
        language: Preferred subtitle language (optional, uses smart fallback if not specified)
        
    Returns:
        Dictionary containing video_id, title, language, and segments
    """
    output_dir = settings.ensure_temp_dir()
    download_id = str(uuid.uuid4())
    download_dir = output_dir / download_id
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / "%(id)s")

    # Build subtitle language priority
    if language and language.lower() not in ["", "auto", "default"]:
        # User specified a language:
        # 1. Original subtitles for that language
        # 2. Auto-generated for that language  
        # 3. Fallback to original -> English -> auto-English
        subtitle_langs = [
            f"{language}-orig",      # Original for specified language
            f"{language}.*",         # Any variant of specified language
            language,                # Exact match
            ".*-orig",               # Any original language
            "en-orig",               # English original
            "en.*",                  # Any English variant
            "en",                    # English
        ]
    else:
        # Default priority: original language -> English -> auto-generated
        subtitle_langs = [
            ".*-orig",               # Original language subtitles (any language)
            "en-orig",               # English original
            "en.*",                  # Any English variant (en, en-US, en-GB, etc.)
            "en",                    # Plain English
        ]

    # Use SRT format - has higher success rate and fewer 429 errors
    ydl_opts = {
        **BASE_YDL_OPTS,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": subtitle_langs,
        "subtitlesformat": "srt/vtt/best",  # Prefer SRT, fallback to VTT
        "outtmpl": output_template,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if not info:
        raise ValueError("Could not extract video information")

    video_id = info.get("id", "")
    title = info.get("title", "Unknown")

    # Find the subtitle file (check for both SRT and VTT)
    subtitle_file = None
    actual_language = language
    
    for file in download_dir.iterdir():
        if file.suffix in [".srt", ".vtt"]:
            subtitle_file = file
            # Extract language from filename if present
            name_parts = file.stem.split(".")
            if len(name_parts) > 1:
                actual_language = name_parts[-1]
            break

    if not subtitle_file:
        # Clean up directory
        shutil.rmtree(download_dir, ignore_errors=True)
        if language:
            raise ValueError(f"No subtitles available for language: {language}")
        else:
            raise ValueError("No subtitles available for this video")

    # Read and parse the subtitle file based on format
    content = subtitle_file.read_text(encoding="utf-8")
    
    if subtitle_file.suffix == ".srt":
        segments = parse_srt_content(content)
    else:
        segments = parse_vtt_content(content)

    # Clean up directory
    shutil.rmtree(download_dir, ignore_errors=True)

    return {
        "video_id": video_id,
        "title": title,
        "language": actual_language,
        "segments": segments,
    }
