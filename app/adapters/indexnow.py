from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.config import settings
from app.models import ChangeEvent


@dataclass(slots=True)
class AdapterResult:
    status: str
    response_code: int | None = None
    response_body: str | None = None
    retryable: bool = False


async def deliver_indexnow(event: ChangeEvent) -> AdapterResult:
    site = event.site
    if not site.indexnow_key:
        return AdapterResult(status="skipped", response_body="IndexNow key is not configured")

    host = urlsplit(site.base_url).netloc
    key_location = site.indexnow_key_location or f"https://{host}/{site.indexnow_key}.txt"
    payload = {
        "host": host,
        "key": site.indexnow_key,
        "keyLocation": key_location,
        "urlList": [event.page.canonical_url],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(settings.indexnow_endpoint, json=payload)
    except httpx.HTTPError as exc:
        return AdapterResult(status="retry", response_body=str(exc), retryable=True)

    body = response.text[:4000]
    if 200 <= response.status_code < 300:
        return AdapterResult(status="success", response_code=response.status_code, response_body=body)
    if response.status_code in {408, 425, 429} or response.status_code >= 500:
        return AdapterResult(
            status="retry",
            response_code=response.status_code,
            response_body=body,
            retryable=True,
        )
    return AdapterResult(status="failed", response_code=response.status_code, response_body=body)
