import logging
import sys
import yt_dlp
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import youtube, media
from app.services.cleanup import start_cleanup_scheduler, stop_cleanup_scheduler

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings.ensure_temp_dir()
    start_cleanup_scheduler()
    yield
    # Shutdown
    stop_cleanup_scheduler()


app = FastAPI(
    title="TubeAPI",
    description="Media download API service powered by yt-dlp",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(youtube.router, prefix="/youtube", tags=["YouTube"])
app.include_router(media.router, prefix="/media", tags=["Media"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint - no authentication required."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "yt_dlp_version": yt_dlp.version.__version__,
    }

