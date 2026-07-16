from __future__ import annotations

import argparse
import asyncio

from app.database import SessionLocal, init_database
from app.services.dispatcher import dispatch_due_retries


async def run(limit: int) -> None:
    init_database()
    with SessionLocal() as db:
        event_ids = await dispatch_due_retries(db, limit=limit)
    print(f"retried={len(event_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch due retry deliveries once.")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()
