from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class Meeting:
    id: str
    org_id: str
    title: str
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class MeetingNote:
    id: str
    meeting_id: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ActionItem:
    id: str
    org_id: str
    title: str
    department: str | None = None
    due_at: datetime | None = None
    status: str = "open"
    event_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class TeamDocument:
    id: str
    org_id: str
    title: str
    kind: str = "doc"
    content: str | None = None
    event_id: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
