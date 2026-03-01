from __future__ import annotations

from smt_os.application.ports.repositories import EventRepository
from smt_os.domain.events.entities import Event


class ListEventsUseCase:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self) -> list[Event]:
        return self._events.list()
