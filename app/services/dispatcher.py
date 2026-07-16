from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.adapters.indexnow import AdapterResult, deliver_indexnow
from app.adapters.local_artifacts import deliver_local_artifact
from app.config import settings
from app.models import ChangeEvent, Delivery, DeliveryStatus, EventStatus


async def _run_channel(event: ChangeEvent, channel: str) -> AdapterResult:
    if channel == "indexnow":
        return await deliver_indexnow(event)
    if channel in {"sitemap", "rss", "changes"}:
        return await deliver_local_artifact(event, channel)
    return AdapterResult(status="failed", response_body=f"Unsupported channel: {channel}")


def _next_retry(attempts: int) -> datetime:
    delay = min(settings.retry_max_seconds, settings.retry_base_seconds * (2 ** max(0, attempts - 1)))
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


async def dispatch_event(db: Session, event_id: str) -> ChangeEvent:
    event = db.scalar(
        select(ChangeEvent)
        .where(ChangeEvent.id == event_id)
        .options(
            selectinload(ChangeEvent.site),
            selectinload(ChangeEvent.page),
            selectinload(ChangeEvent.deliveries),
        )
    )
    if event is None:
        raise LookupError("Event not found")

    event.status = EventStatus.processing.value
    db.commit()

    for delivery in event.deliveries:
        if delivery.status in {DeliveryStatus.success.value, DeliveryStatus.skipped.value}:
            continue
        if delivery.attempts >= settings.max_delivery_attempts:
            delivery.status = DeliveryStatus.failed.value
            continue

        delivery.status = DeliveryStatus.processing.value
        delivery.attempts += 1
        delivery.updated_at = datetime.now(timezone.utc)
        db.commit()

        result = await _run_channel(event, delivery.channel)
        delivery.status = result.status
        delivery.response_code = result.response_code
        delivery.response_body = result.response_body
        delivery.updated_at = datetime.now(timezone.utc)
        if result.status in {DeliveryStatus.success.value, DeliveryStatus.skipped.value}:
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.next_retry_at = None
        elif result.retryable and delivery.attempts < settings.max_delivery_attempts:
            delivery.next_retry_at = _next_retry(delivery.attempts)
        else:
            delivery.next_retry_at = None
        db.commit()

    statuses = {delivery.status for delivery in event.deliveries}
    if statuses.issubset({DeliveryStatus.success.value, DeliveryStatus.skipped.value}):
        event.status = EventStatus.completed.value
    elif DeliveryStatus.retry.value in statuses or DeliveryStatus.pending.value in statuses:
        event.status = EventStatus.partial.value
    elif DeliveryStatus.success.value in statuses or DeliveryStatus.skipped.value in statuses:
        event.status = EventStatus.partial.value
    else:
        event.status = EventStatus.failed.value
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


async def dispatch_due_retries(db: Session, limit: int = 100) -> list[str]:
    now = datetime.now(timezone.utc)
    event_ids = list(
        db.scalars(
            select(Delivery.event_id)
            .where(
                Delivery.status == DeliveryStatus.retry.value,
                Delivery.next_retry_at.is_not(None),
                Delivery.next_retry_at <= now,
            )
            .limit(limit)
        )
    )
    unique_ids = list(dict.fromkeys(event_ids))
    for event_id in unique_ids:
        await dispatch_event(db, event_id)
    return unique_ids
