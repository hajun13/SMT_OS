from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from smt_os.application.ports.repositories import EventRepository


class EventNotFoundBySlugError(ValueError):
    pass


@dataclass(slots=True)
class PublicEventView:
    id: str
    slug: str
    title: str
    template: str
    start_at: datetime
    end_at: datetime
    capacity: int


class GetPublicEventUseCase:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, slug: str) -> PublicEventView:
        event = self._events.get_by_slug(slug)
        if event is None:
            raise EventNotFoundBySlugError("event not found")

        return PublicEventView(
            id=event.id,
            slug=event.slug,
            title=event.title,
            template=event.template.value,
            start_at=event.start_at,
            end_at=event.end_at,
            capacity=event.capacity,
        )
