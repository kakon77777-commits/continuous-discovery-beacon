from __future__ import annotations

from app.adapters.indexnow import AdapterResult
from app.models import ChangeEvent


async def deliver_local_artifact(event: ChangeEvent, channel: str) -> AdapterResult:
    # Sitemap, RSS and changes streams are generated live from the database.
    # A successful transaction means the public representation is immediately current.
    return AdapterResult(
        status="success",
        response_code=200,
        response_body=f"{channel} is database-backed and now reflects event {event.id}",
    )
