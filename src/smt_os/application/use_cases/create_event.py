from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from smt_os.application.ports.repositories import EventRepository
from smt_os.domain.common.enums import EventTemplate
from smt_os.domain.events.entities import Event, EventModules


@dataclass(slots=True)
class CreateEventCommand:
    org_id: str
    slug: str
    title: str
    template: EventTemplate
    start_at: datetime
    end_at: datetime
    capacity: int


class CreateEventUseCase:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, command: CreateEventCommand) -> Event:
        modules = EventModules(groups=True)
        if command.template == EventTemplate.CAMP:
            modules.lodging = True
            modules.buses = True

        event = Event(
            id=str(uuid4()),
            org_id=command.org_id,
            slug=command.slug,
            title=command.title,
            template=command.template,
            start_at=command.start_at,
            end_at=command.end_at,
            capacity=command.capacity,
            modules=modules,
        )
        self._events.save(event)
        return event
