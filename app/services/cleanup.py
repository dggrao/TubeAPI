import shutil
import time
import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def cleanup_old_files():
    """
    Remove files and directories older than the configured max age.
    
    This runs as a scheduled background task to catch orphaned files
    that weren't cleaned up after download (e.g., due to crashes or
    incomplete downloads).
    """
    temp_dir = settings.tubeapi_temp_dir
    max_age = settings.tubeapi_cleanup_max_age
    current_time = time.time()
    removed_count = 0

    if not temp_dir.exists():
        return

    try:
        for item in temp_dir.iterdir():
            try:
                # Check modification time
                item_stat = item.stat()
                age = current_time - item_stat.st_mtime

                if age > max_age:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Error cleaning up {item}: {e}")
                continue

        if removed_count > 0:
            logger.info(f"Cleanup: removed {removed_count} old items")

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")


def start_cleanup_scheduler():
    """Start the background cleanup scheduler."""
    global _scheduler

    if _scheduler is not None:
        return  # Already running

    _scheduler = BackgroundScheduler()
    
    # Run cleanup every 30 minutes
    _scheduler.add_job(
        cleanup_old_files,
        'interval',
        minutes=30,
        id='cleanup_job',
        replace_existing=True,
    )
    
    # Also run once at startup (after a short delay)
    _scheduler.add_job(
        cleanup_old_files,
        'date',
        id='cleanup_startup',
    )
    
    _scheduler.start()
    logger.info("Cleanup scheduler started")


def stop_cleanup_scheduler():
    """Stop the background cleanup scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Cleanup scheduler stopped")


def cleanup_download_directory(directory: Path):
    """
    Immediately clean up a download directory.
    
    This is used as a background task after file responses are sent.
    
    Args:
        directory: The download directory to remove
    """
    try:
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {directory}: {e}")

