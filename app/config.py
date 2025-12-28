import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Authentication
    tubeapi_user: str = "admin"
    tubeapi_pass: str = "changeme"

    # Server
    tubeapi_port: int = 8000

    # File management
    tubeapi_temp_dir: Path = Path("/tmp/tubeapi")
    tubeapi_cleanup_max_age: int = 7200  # 2 hours in seconds

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_bucket: str = "yt-stock"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_temp_dir(self) -> Path:
        """Create temp directory if it doesn't exist."""
        self.tubeapi_temp_dir.mkdir(parents=True, exist_ok=True)
        return self.tubeapi_temp_dir


# Global settings instance
settings = Settings()

