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




class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    yt_dlp_version: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: Optional[str] = None


# Request body schemas
class VideoRequest(BaseModel):
    """Request body for video download."""

    url: str
    quality: Optional[str] = "1080"  # Default to 1080p or less
    proxy: Optional[str] = None








class MediaRequest(BaseModel):
    """Request body for generic media download."""

    url: str
    proxy: Optional[str] = None
