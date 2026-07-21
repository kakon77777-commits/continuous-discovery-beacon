from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Site


def require_write_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_token:
        return
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    supplied = authorization.removeprefix(prefix)
    if not hmac.compare_digest(supplied, settings.api_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")


def generate_submit_token() -> str:
    return secrets.token_urlsafe(32)


def hash_submit_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_site_submit_token(db: Session, site_id: str, authorization: str | None) -> None:
    """Per-site event-submission auth: a leaked token can only ever act as one site."""
    if not settings.api_token:
        return
    site = db.get(Site, site_id)
    if site is None or not site.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or disabled site")
    if not site.submit_token_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Site has no submit token configured")
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    supplied = authorization.removeprefix(prefix)
    if not hmac.compare_digest(hash_submit_token(supplied), site.submit_token_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")
