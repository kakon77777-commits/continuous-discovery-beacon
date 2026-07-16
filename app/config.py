from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("CDB_APP_NAME", "Continuous Discovery Beacon")
    app_version: str = os.getenv("CDB_APP_VERSION", "0.1.0")
    environment: str = os.getenv("CDB_ENV", "development")
    database_url: str = os.getenv("CDB_DATABASE_URL", "sqlite:///./data/cdb.sqlite3")
    public_base_url: str = os.getenv("CDB_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    api_token: str = os.getenv("CDB_API_TOKEN", "")
    indexnow_endpoint: str = os.getenv("CDB_INDEXNOW_ENDPOINT", "https://api.indexnow.org/indexnow")
    request_timeout_seconds: float = float(os.getenv("CDB_REQUEST_TIMEOUT_SECONDS", "10"))
    max_delivery_attempts: int = int(os.getenv("CDB_MAX_DELIVERY_ATTEMPTS", "5"))
    retry_base_seconds: int = int(os.getenv("CDB_RETRY_BASE_SECONDS", "60"))
    retry_max_seconds: int = int(os.getenv("CDB_RETRY_MAX_SECONDS", "3600"))
    default_feed_limit: int = int(os.getenv("CDB_DEFAULT_FEED_LIMIT", "50"))

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        return Path(self.database_url.removeprefix(prefix))


settings = Settings()
