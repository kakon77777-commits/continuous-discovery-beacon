from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal, init_database
from app.models import Site
from app.schemas import EventCreate
from app.services.events import create_event


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a demo site and event.")
    parser.add_argument("--site-id", default="logic_evemisslab")
    parser.add_argument("--name", default="EVEMISSLAB Logic")
    parser.add_argument("--base-url", default="https://logic.evemisslab.com")
    parser.add_argument("--url", default="https://logic.evemisslab.com/timeline/")
    args = parser.parse_args()

    init_database()
    with SessionLocal() as db:
        site = db.scalar(select(Site).where(Site.id == args.site_id))
        if site is None:
            site = Site(id=args.site_id, name=args.name, base_url=args.base_url.rstrip("/"), enabled=True)
            db.add(site)
            db.commit()
        event, duplicate = create_event(
            db,
            EventCreate(
                site_id=args.site_id,
                url=args.url,
                event_type="created",
                modified_at=datetime.now(timezone.utc),
                content_hash="sha256:demo",
                title="Timeline",
                summary="Demo discovery event.",
                auto_dispatch=False,
            ),
        )
        print(f"event={event.id} duplicate={duplicate}")


if __name__ == "__main__":
    main()
