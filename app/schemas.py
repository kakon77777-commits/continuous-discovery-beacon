from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models import EventType


class SiteCreate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,95}$")
    name: str = Field(min_length=1, max_length=255)
    base_url: HttpUrl
    enabled: bool = True
    indexnow_key: str | None = Field(default=None, max_length=255)
    indexnow_key_location: HttpUrl | None = None


class SiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    base_url: str
    enabled: bool
    indexnow_key_location: str | None
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    site_id: str
    url: HttpUrl
    event_type: EventType
    modified_at: datetime | None = None
    content_hash: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=4000)
    status_code: int = Field(default=200, ge=100, le=599)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    channels: list[Literal["indexnow", "sitemap", "rss", "changes"]] = Field(
        default_factory=lambda: ["indexnow", "sitemap", "rss", "changes"]
    )
    auto_dispatch: bool = True

    @field_validator("channels")
    @classmethod
    def unique_channels(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("channels must not be empty")
        return list(dict.fromkeys(value))


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    channel: str
    status: str
    attempts: int
    response_code: int | None
    response_body: str | None
    next_retry_at: datetime | None
    delivered_at: datetime | None


class EventRead(BaseModel):
    id: str
    site_id: str
    page_id: str
    url: str
    canonical_url: str
    event_type: str
    priority: float
    status: str
    created_at: datetime
    processed_at: datetime | None
    duplicate: bool = False
    deliveries: list[DeliveryRead] = Field(default_factory=list)


class EventListItem(BaseModel):
    id: str
    site_id: str
    url: str
    event_type: str
    priority: float
    status: str
    created_at: datetime


class DispatchResult(BaseModel):
    event_id: str
    event_status: str
    deliveries: list[DeliveryRead]
