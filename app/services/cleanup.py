import datetime
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
    Remove local files and directories older than tubeapi_cleanup_max_age.

    Runs as a scheduled background task to catch orphaned files left behind
    by crashes or incomplete downloads.
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
                age = current_time - item.stat().st_mtime
                if age > max_age:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    removed_count += 1
            except Exception as exc:
                logger.warning("Error cleaning up %s: %s", item, exc)

        if removed_count > 0:
            logger.info("Cleanup: removed %d old local items", removed_count)

    except Exception as exc:
        logger.error("Cleanup task failed: %s", exc)


def start_cleanup_scheduler():
    """Start the background cleanup scheduler."""
    global _scheduler

    if _scheduler is not None:
        return  # Already running

    _scheduler = BackgroundScheduler()

    # Run local-file cleanup every 30 minutes
    _scheduler.add_job(
        cleanup_old_files,
        "interval",
        minutes=30,
        id="cleanup_job",
        replace_existing=True,
    )

    # Also run once shortly after startup
    _scheduler.add_job(
        cleanup_old_files,
        "date",
        id="cleanup_startup",
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
    """Immediately remove a local download directory (used as a background task)."""
    try:
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
    except Exception as exc:
        logger.warning("Failed to cleanup directory %s: %s", directory, exc)


def schedule_gcs_deletion(filename: str) -> None:
    """
    Schedule deletion of a GCS object after tubeapi_file_ttl seconds (default 1h).

    Uses the global APScheduler instance so the job survives across requests.
    The import of delete_gcs_object is deferred to avoid circular imports.
    """
    if _scheduler is None:
        logger.warning("Scheduler not running; GCS object %s will NOT be auto-deleted.", filename)
        return

    from app.services.storage import delete_gcs_object  # deferred to avoid circular import

    run_date = datetime.datetime.now() + datetime.timedelta(seconds=settings.tubeapi_file_ttl)
    _scheduler.add_job(
        delete_gcs_object,
        "date",
        run_date=run_date,
        args=[filename],
        id=f"gcs_delete_{filename}",
        replace_existing=True,
    )
    logger.info("Scheduled GCS deletion of %s at %s", filename, run_date.isoformat())
