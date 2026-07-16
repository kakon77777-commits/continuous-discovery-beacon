from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ChangeEvent, Delivery, EventStatus, Page, Site
from app.schemas import EventCreate, EventRead
from app.services.url_normalizer import canonicalize_url


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def make_dedup_key(payload: EventCreate, canonical_url: str, modified_at: datetime) -> str:
    identity = "|".join(
        [
            payload.site_id,
            canonical_url,
            payload.event_type.value,
            payload.content_hash or modified_at.isoformat(),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def serialize_event(event: ChangeEvent, duplicate: bool = False) -> EventRead:
    return EventRead(
        id=event.id,
        site_id=event.site_id,
        page_id=event.page_id,
        url=event.page.url,
        canonical_url=event.page.canonical_url,
        event_type=event.event_type,
        priority=event.priority,
        status=event.status,
        created_at=event.created_at,
        processed_at=event.processed_at,
        duplicate=duplicate,
        deliveries=event.deliveries,
    )


def create_event(db: Session, payload: EventCreate) -> tuple[ChangeEvent, bool]:
    site = db.get(Site, payload.site_id)
    if site is None or not site.enabled:
        raise LookupError("Unknown or disabled site")

    canonical_url = canonicalize_url(str(payload.url), site.base_url)
    modified_at = _utc(payload.modified_at)
    dedup_key = make_dedup_key(payload, canonical_url, modified_at)

    existing = db.scalar(select(ChangeEvent).where(ChangeEvent.dedup_key == dedup_key))
    if existing is not None:
        return existing, True

    page = db.scalar(
        select(Page).where(Page.site_id == site.id, Page.canonical_url == canonical_url)
    )
    if page is None:
        page = Page(
            site_id=site.id,
            url=str(payload.url),
            canonical_url=canonical_url,
            title=payload.title,
            summary=payload.summary,
            content_hash=payload.content_hash,
            last_modified=modified_at,
            last_seen=modified_at,
            status_code=payload.status_code,
            is_deleted=payload.event_type.value == "deleted",
        )
        db.add(page)
        db.flush()
    else:
        page.url = str(payload.url)
        page.previous_hash = page.content_hash
        if payload.content_hash is not None:
            page.content_hash = payload.content_hash
        page.title = payload.title or page.title
        page.summary = payload.summary or page.summary
        page.last_modified = modified_at
        page.last_seen = modified_at
        page.status_code = payload.status_code
        page.is_deleted = payload.event_type.value == "deleted"

    event_payload = {
        "site_id": site.id,
        "url": str(payload.url),
        "canonical_url": canonical_url,
        "event_type": payload.event_type.value,
        "modified_at": modified_at.isoformat(),
        "content_hash": payload.content_hash,
        "priority": payload.priority,
        "channels": payload.channels,
    }
    event = ChangeEvent(
        site_id=site.id,
        page_id=page.id,
        event_type=payload.event_type.value,
        priority=payload.priority,
        payload_json=json.dumps(event_payload, ensure_ascii=False, sort_keys=True),
        dedup_key=dedup_key,
        status=EventStatus.pending.value,
    )
    db.add(event)
    db.flush()
    for channel in payload.channels:
        db.add(Delivery(event_id=event.id, channel=channel))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ChangeEvent).where(ChangeEvent.dedup_key == dedup_key))
        if existing is None:
            raise
        return existing, True
    db.refresh(event)
    return event, False
