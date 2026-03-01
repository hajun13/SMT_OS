from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

router = APIRouter(include_in_schema=False)


@router.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/console")
def console() -> FileResponse:
    return FileResponse(STATIC_DIR / "console.html")


@router.get("/e/{slug}")
def public_event_landing(slug: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "event-landing.html")


@router.get("/e/{slug}/register")
def public_event_register(slug: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "event-register.html")


@router.get("/e/{slug}/ticket")
def public_event_ticket(slug: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "event-ticket.html")
