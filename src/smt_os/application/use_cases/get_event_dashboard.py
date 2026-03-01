from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import CheckinRepository, ParticipantRepository
from smt_os.domain.common.enums import CheckinType


@dataclass(slots=True)
class GetEventDashboardQuery:
    event_id: str
    church_or_school: str | None = None
    grade: str | None = None


@dataclass(slots=True)
class EventDashboardResult:
    registered_count: int
    checked_in_count: int


class GetEventDashboardUseCase:
    def __init__(self, participants: ParticipantRepository, checkins: CheckinRepository) -> None:
        self._participants = participants
        self._checkins = checkins

    def execute(self, query: GetEventDashboardQuery) -> EventDashboardResult:
        participants = self._participants.list_by_event(
            event_id=query.event_id,
            church_or_school=query.church_or_school,
            grade=query.grade,
        )
        ids = {participant.id for participant in participants}
        checked_in_count = self._checkins.count_for_participants(
            event_id=query.event_id,
            participant_ids=ids,
            checkin_type=CheckinType.ENTRY,
        )
        return EventDashboardResult(
            registered_count=len(participants),
            checked_in_count=checked_in_count,
        )
