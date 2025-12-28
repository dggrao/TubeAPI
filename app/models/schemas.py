from typing import Optional

from pydantic import BaseModel, HttpUrl


class VideoInfo(BaseModel):
    """Video metadata response schema."""

    id: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail: Optional[str] = None
    webpage_url: str
    extractor: str
    formats_available: Optional[list[str]] = None


class TranscriptSegment(BaseModel):
    """Single transcript segment."""

    start: float  # Start time in seconds
    duration: float  # Duration in seconds
    text: str


class TranscriptResponse(BaseModel):
    """Transcript response schema."""

    video_id: str
    title: str
    language: str
    segments: list[TranscriptSegment]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    yt_dlp_version: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: Optional[str] = None

