from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import EventRepository
from smt_os.domain.events.entities import Event


class DeleteEventNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class DeleteEventUseCase:
    events: EventRepository

    def execute(self, event_id: str) -> Event:
        deleted = self.events.delete(event_id)
        if deleted is None:
            raise DeleteEventNotFoundError("event not found")
        return deleted
