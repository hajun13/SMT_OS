from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from smt_os.application.ports.repositories import CheckinRepository, ParticipantRepository, TicketRepository
from smt_os.domain.checkins.entities import Checkin
from smt_os.domain.common.enums import CheckinType


class InvalidTicketError(ValueError):
    pass


class DuplicateCheckinError(ValueError):
    pass


@dataclass(slots=True)
class CheckinByTokenCommand:
    event_id: str
    token: str
    checkin_type: CheckinType = CheckinType.ENTRY


class CheckinByTokenUseCase:
    def __init__(
        self,
        tickets: TicketRepository,
        participants: ParticipantRepository,
        checkins: CheckinRepository,
    ) -> None:
        self._tickets = tickets
        self._participants = participants
        self._checkins = checkins

    def execute(self, command: CheckinByTokenCommand) -> Checkin:
        ticket = self._tickets.find_by_token(command.token)
        if ticket is None or ticket.status != "issued":
            raise InvalidTicketError("invalid ticket")

        participant = self._participants.get(ticket.participant_id)
        if participant is None or participant.event_id != command.event_id:
            raise InvalidTicketError("ticket does not belong to event")

        if self._checkins.exists(command.event_id, participant.id, command.checkin_type):
            raise DuplicateCheckinError("duplicate checkin")

        checkin = Checkin(
            id=str(uuid4()),
            event_id=command.event_id,
            participant_id=participant.id,
            type=command.checkin_type,
        )
        self._checkins.save(checkin)
        return checkin

    def execute_for_participant(
        self,
        event_id: str,
        participant_id: str,
        checkin_type: CheckinType = CheckinType.ENTRY,
    ) -> Checkin:
        participant = self._participants.get(participant_id)
        if participant is None or participant.event_id != event_id:
            raise InvalidTicketError("participant does not belong to event")

        ticket = self._tickets.find_by_participant_id(participant_id)
        if ticket is None or ticket.status != "issued":
            raise InvalidTicketError("invalid ticket")

        if self._checkins.exists(event_id, participant.id, checkin_type):
            raise DuplicateCheckinError("duplicate checkin")

        checkin = Checkin(
            id=str(uuid4()),
            event_id=event_id,
            participant_id=participant.id,
            type=checkin_type,
        )
        self._checkins.save(checkin)
        return checkin
