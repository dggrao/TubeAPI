import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Verify HTTP Basic Auth credentials.
    
    Returns the username if valid, raises HTTPException if invalid.
    Uses constant-time comparison to prevent timing attacks.
    """
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.tubeapi_user.encode("utf-8"),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.tubeapi_pass.encode("utf-8"),
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username

