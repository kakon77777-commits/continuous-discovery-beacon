from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class EventType(str, enum.Enum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
    redirected = "redirected"
    restored = "restored"
    metadata_changed = "metadata_changed"
    structured_data_changed = "structured_data_changed"


class EventStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    partial = "partial"
    failed = "failed"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    skipped = "skipped"
    retry = "retry"
    failed = "failed"


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    indexnow_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indexnow_key_location: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    pages: Mapped[list[Page]] = relationship(back_populates="site", cascade="all, delete-orphan")
    events: Mapped[list[ChangeEvent]] = relationship(back_populates="site", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("site_id", "canonical_url", name="uq_pages_site_canonical"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True, default=lambda: new_id("page"))
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    site: Mapped[Site] = relationship(back_populates="pages")
    events: Mapped[list[ChangeEvent]] = relationship(back_populates="page", cascade="all, delete-orphan")


class ChangeEvent(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("dedup_key", name="uq_events_dedup_key"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True, default=lambda: new_id("evt"))
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EventStatus.pending.value, index=True)

    site: Mapped[Site] = relationship(back_populates="events")
    page: Mapped[Page] = relationship(back_populates="events")
    deliveries: Mapped[list[Delivery]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("event_id", "channel", name="uq_delivery_event_channel"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True, default=lambda: new_id("del"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DeliveryStatus.pending.value)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    event: Mapped[ChangeEvent] = relationship(back_populates="deliveries")
