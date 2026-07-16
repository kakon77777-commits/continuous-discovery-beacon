from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import ChangeEvent, Page, Site


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_sitemap(db: Session, site_id: str | None = None) -> str:
    query = select(Page).where(Page.is_deleted.is_(False), Page.status_code < 400).order_by(Page.canonical_url)
    if site_id:
        query = query.where(Page.site_id == site_id)
    pages = list(db.scalars(query))
    rows = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages:
        rows.extend(
            [
                "  <url>",
                f"    <loc>{escape(page.canonical_url)}</loc>",
                f"    <lastmod>{iso(page.last_modified)}</lastmod>",
                "  </url>",
            ]
        )
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def build_rss(db: Session, site_id: str | None = None, limit: int | None = None) -> str:
    limit = limit or settings.default_feed_limit
    query = (
        select(ChangeEvent)
        .join(ChangeEvent.page)
        .options(selectinload(ChangeEvent.page), selectinload(ChangeEvent.site))
        .where(ChangeEvent.event_type.in_(["created", "updated", "restored", "metadata_changed", "structured_data_changed"]))
        .order_by(desc(ChangeEvent.created_at))
        .limit(limit)
    )
    if site_id:
        query = query.where(ChangeEvent.site_id == site_id)
    events = list(db.scalars(query))
    title = "Continuous Discovery Beacon Changes"
    link = settings.public_base_url
    if site_id:
        site = db.get(Site, site_id)
        if site:
            title = f"{site.name} — Content Changes"
            link = site.base_url
    rows = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        '<rss version="2.0">',
        "<channel>",
        f"  <title>{escape(title)}</title>",
        f"  <link>{escape(link)}</link>",
        "  <description>Created and updated public content.</description>",
        f"  <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>",
    ]
    for event in events:
        title_text = event.page.title or event.page.canonical_url
        description = event.page.summary or f"Content event: {event.event_type}"
        rows.extend(
            [
                "  <item>",
                f"    <title>{escape(title_text)}</title>",
                f"    <link>{escape(event.page.canonical_url)}</link>",
                f"    <guid isPermaLink=\"false\">{escape(event.id)}</guid>",
                f"    <pubDate>{format_datetime(event.created_at if event.created_at.tzinfo else event.created_at.replace(tzinfo=timezone.utc))}</pubDate>",
                f"    <description>{escape(description)}</description>",
                "  </item>",
            ]
        )
    rows.extend(["</channel>", "</rss>"])
    return "\n".join(rows) + "\n"


def build_changes_jsonl(db: Session, site_id: str | None = None, limit: int = 1000) -> str:
    query = (
        select(ChangeEvent)
        .options(selectinload(ChangeEvent.page))
        .order_by(ChangeEvent.created_at)
        .limit(limit)
    )
    if site_id:
        query = query.where(ChangeEvent.site_id == site_id)
    lines: list[str] = []
    for event in db.scalars(query):
        lines.append(
            json.dumps(
                {
                    "event_id": event.id,
                    "site_id": event.site_id,
                    "url": event.page.canonical_url,
                    "event": event.event_type,
                    "time": iso(event.created_at),
                    "status": event.status,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")
