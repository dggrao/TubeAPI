import datetime
import logging
import mimetypes
from pathlib import Path

import google.auth
import google.auth.transport.requests
from google.cloud import storage

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> storage.Client:
    """Get GCS client using Application Default Credentials or key file."""
    return storage.Client()


def _generate_signed_url(blob: storage.Blob) -> str:
    """
    Generate a V4 signed URL for a GCS blob.

    Works with:
    - Service account key file (GOOGLE_APPLICATION_CREDENTIALS)
    - GCE Workload Identity / attached service account
    """
    expiration = datetime.timedelta(seconds=settings.tubeapi_file_ttl)
    credentials, _ = google.auth.default()

    auth_request = google.auth.transport.requests.Request()
    if not credentials.valid:
        credentials.refresh(auth_request)

    # Service account key file: credentials carry a private key for signing
    if hasattr(credentials, "sign_bytes"):
        return blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET",
        )

    # GCE / Workload Identity: delegate signing to the IAM API
    service_account_email = getattr(credentials, "service_account_email", None)
    if service_account_email:
        return blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET",
            service_account_email=service_account_email,
            access_token=credentials.token,
        )

    raise RuntimeError(
        "Cannot generate signed URL: credentials don't support signing. "
        "Set GOOGLE_APPLICATION_CREDENTIALS to a service account key file, "
        "or run on a GCP VM with an attached service account that has "
        "the 'Service Account Token Creator' role."
    )


def upload_file(file_path: Path, filename: str = None) -> tuple[str, str]:
    """
    Upload a file to GCS and return (signed_url, blob_name).

    The signed URL expires after settings.tubeapi_file_ttl seconds (default 1h).
    The caller is responsible for scheduling GCS deletion via schedule_gcs_deletion().

    Args:
        file_path: Path to the local file.
        filename:  Blob name in GCS. Defaults to file_path.name.

    Returns:
        Tuple of (signed_url, gcs_blob_name).
    """
    if not filename:
        filename = file_path.name

    content_type = "application/octet-stream"
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        content_type = mime

    client = _get_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(filename)

    blob.upload_from_filename(str(file_path), content_type=content_type)
    logger.info("Uploaded %s to gs://%s/%s", filename, settings.gcs_bucket_name, filename)

    signed_url = _generate_signed_url(blob)
    logger.info("Signed URL generated for %s (TTL=%ds)", filename, settings.tubeapi_file_ttl)

    return signed_url, filename


def delete_gcs_object(filename: str) -> None:
    """Delete an object from the GCS bucket."""
    try:
        client = _get_client()
        bucket = client.bucket(settings.gcs_bucket_name)
        blob = bucket.blob(filename)
        blob.delete()
        logger.info("Deleted gs://%s/%s", settings.gcs_bucket_name, filename)
    except Exception as exc:
        logger.warning("Failed to delete GCS object %s: %s", filename, exc)
