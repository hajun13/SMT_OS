from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import ParticipantRepository, TicketRepository


class TicketNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class PublicTicketView:
    event_id: str
    participant_name: str
    ticket_status: str


class GetPublicTicketUseCase:
    def __init__(self, tickets: TicketRepository, participants: ParticipantRepository) -> None:
        self._tickets = tickets
        self._participants = participants

    def execute(self, token: str) -> PublicTicketView:
        ticket = self._tickets.find_by_token(token)
        if ticket is None:
            raise TicketNotFoundError("ticket not found")

        participant = self._participants.get(ticket.participant_id)
        if participant is None:
            raise TicketNotFoundError("participant not found")

        return PublicTicketView(
            event_id=participant.event_id,
            participant_name=participant.name,
            ticket_status=ticket.status,
        )
