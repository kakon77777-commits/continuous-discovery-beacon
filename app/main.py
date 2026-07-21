from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import SessionLocal, get_db, init_database
from app.models import ChangeEvent, Delivery, EventStatus, Page, Site
from app.schemas import DispatchResult, EventCreate, EventListItem, EventRead, SiteCreate, SiteCreateResponse, SiteRead
from app.security import generate_submit_token, hash_submit_token, require_site_submit_token, require_write_token
from app.services.dispatcher import dispatch_event
from app.services.events import create_event, serialize_event
from app.services.feeds import build_changes_jsonl, build_rss, build_sitemap
from app.services.url_normalizer import normalize_base_url

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Event-driven website discovery and indexing signal MVP.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def _dispatch_in_new_session(event_id: str) -> None:
    with SessionLocal() as db:
        await dispatch_event(db, event_id)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@app.post("/api/v1/sites", response_model=SiteCreateResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_token)])
def create_site(payload: SiteCreate, db: Session = Depends(get_db)) -> SiteCreateResponse:
    if db.get(Site, payload.id):
        raise HTTPException(status_code=409, detail="Site id already exists")
    base_url = normalize_base_url(str(payload.base_url))
    if db.scalar(select(Site).where(Site.base_url == base_url)):
        raise HTTPException(status_code=409, detail="Site base_url already exists")
    submit_token = generate_submit_token()
    site = Site(
        id=payload.id,
        name=payload.name,
        base_url=base_url,
        enabled=payload.enabled,
        indexnow_key=payload.indexnow_key,
        indexnow_key_location=str(payload.indexnow_key_location) if payload.indexnow_key_location else None,
        submit_token_hash=hash_submit_token(submit_token),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return SiteCreateResponse(**SiteRead.model_validate(site).model_dump(), submit_token=submit_token)


@app.get("/api/v1/sites", response_model=list[SiteRead])
def list_sites(db: Session = Depends(get_db)) -> list[Site]:
    return list(db.scalars(select(Site).order_by(Site.name)))


@app.post("/api/v1/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def post_event(
    payload: EventCreate,
    background_tasks: BackgroundTasks,
    response: Response,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> EventRead:
    require_site_submit_token(db, payload.site_id, authorization)
    try:
        event, duplicate = create_event(db, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if duplicate:
        response.status_code = status.HTTP_200_OK
    elif payload.auto_dispatch:
        background_tasks.add_task(_dispatch_in_new_session, event.id)
    return serialize_event(event, duplicate=duplicate)


@app.get("/api/v1/events", response_model=list[EventListItem])
def list_events(
    site_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[EventListItem]:
    query = select(ChangeEvent).options(selectinload(ChangeEvent.page)).order_by(desc(ChangeEvent.created_at)).limit(limit)
    if site_id:
        query = query.where(ChangeEvent.site_id == site_id)
    return [
        EventListItem(
            id=event.id,
            site_id=event.site_id,
            url=event.page.canonical_url,
            event_type=event.event_type,
            priority=event.priority,
            status=event.status,
            created_at=event.created_at,
        )
        for event in db.scalars(query)
    ]


@app.get("/api/v1/events/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> EventRead:
    event = db.scalar(
        select(ChangeEvent)
        .where(ChangeEvent.id == event_id)
        .options(selectinload(ChangeEvent.page), selectinload(ChangeEvent.deliveries))
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return serialize_event(event)


@app.post("/api/v1/events/{event_id}/dispatch", response_model=DispatchResult, dependencies=[Depends(require_write_token)])
async def dispatch(event_id: str, db: Session = Depends(get_db)) -> DispatchResult:
    try:
        event = await dispatch_event(db, event_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DispatchResult(event_id=event.id, event_status=event.status, deliveries=event.deliveries)


@app.get("/sitemap.xml")
def sitemap(site_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    return Response(content=build_sitemap(db, site_id), media_type="application/xml")


@app.get("/feed.xml")
def rss(site_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    return Response(content=build_rss(db, site_id), media_type="application/rss+xml")


@app.get("/changes.jsonl")
def changes(site_id: str | None = None, limit: int = Query(default=1000, ge=1, le=10000), db: Session = Depends(get_db)) -> Response:
    return PlainTextResponse(content=build_changes_jsonl(db, site_id, limit), media_type="application/x-ndjson")


@app.get("/.well-known/discovery.json")
def discovery(db: Session = Depends(get_db)) -> JSONResponse:
    sites = list(db.scalars(select(Site).where(Site.enabled.is_(True)).order_by(Site.id)))
    return JSONResponse(
        {
            "service": settings.app_name,
            "version": settings.app_version,
            "canonical": settings.public_base_url,
            "sitemap": f"{settings.public_base_url}/sitemap.xml",
            "feed": f"{settings.public_base_url}/feed.xml",
            "change_stream": f"{settings.public_base_url}/changes.jsonl",
            "api": f"{settings.public_base_url}/docs",
            "sites": [{"id": site.id, "name": site.name, "base_url": site.base_url} for site in sites],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    sites = list(db.scalars(select(Site).order_by(Site.name)))
    events = list(
        db.scalars(
            select(ChangeEvent)
            .options(selectinload(ChangeEvent.page), selectinload(ChangeEvent.deliveries))
            .order_by(desc(ChangeEvent.created_at))
            .limit(30)
        )
    )
    counts = {
        "sites": db.scalar(select(func.count()).select_from(Site)) or 0,
        "pages": db.scalar(select(func.count()).select_from(Page)) or 0,
        "events": db.scalar(select(func.count()).select_from(ChangeEvent)) or 0,
        "pending": db.scalar(select(func.count()).select_from(ChangeEvent).where(ChangeEvent.status.in_([EventStatus.pending.value, EventStatus.processing.value, EventStatus.partial.value]))) or 0,
        "deliveries": db.scalar(select(func.count()).select_from(Delivery)) or 0,
    }
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"settings": settings, "sites": sites, "events": events, "counts": counts},
    )
