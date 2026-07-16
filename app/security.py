from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.config import settings


def require_write_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_token:
        return
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    supplied = authorization.removeprefix(prefix)
    if not hmac.compare_digest(supplied, settings.api_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")
