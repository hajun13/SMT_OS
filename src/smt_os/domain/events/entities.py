from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from smt_os.domain.common.enums import EventTemplate


@dataclass(slots=True)
class EventModules:
    seats: bool = False
    meals: bool = False
    groups: bool = True
    activities: bool = False
    lodging: bool = False
    buses: bool = False


@dataclass(slots=True)
class Event:
    id: str
    org_id: str
    slug: str
    title: str
    template: EventTemplate
    start_at: datetime
    end_at: datetime
    capacity: int
    modules: EventModules = field(default_factory=EventModules)
