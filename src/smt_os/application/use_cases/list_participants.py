from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import ParticipantRepository, TicketRepository


@dataclass(slots=True)
class ListParticipantsQuery:
    event_id: str
    church_or_school: str | None = None
    grade: str | None = None
    q: str | None = None


@dataclass(slots=True)
class ParticipantView:
    participant_id: str
    name: str
    church_or_school: str | None
    grade: str | None
    participant_role: str | None
    phone: str | None
    registration_fee_paid: bool | None
    refund_requested: bool | None
    refund_status: str | None
    refund_reason: str | None
    refund_processed_by: str | None
    refund_processed_at: str | None
    ticket_status: str | None


class ListParticipantsUseCase:
    def __init__(self, participants: ParticipantRepository, tickets: TicketRepository) -> None:
        self._participants = participants
        self._tickets = tickets

    def execute(self, query: ListParticipantsQuery) -> list[ParticipantView]:
        items = self._participants.list_by_event(
            event_id=query.event_id,
            church_or_school=query.church_or_school,
            grade=query.grade,
            name_query=query.q,
        )
        result: list[ParticipantView] = []
        for participant in items:
            ticket = self._tickets.find_by_participant_id(participant.id)
            role = participant.answers.get("participant_role")
            phone = participant.answers.get("phone")
            paid = participant.answers.get("registration_fee_paid")
            refund_requested = participant.answers.get("refund_requested")
            refund_status = participant.answers.get("refund_status")
            refund_reason = participant.answers.get("refund_reason")
            refund_processed_by = participant.answers.get("refund_processed_by")
            refund_processed_at = participant.answers.get("refund_processed_at")
            result.append(
                ParticipantView(
                    participant_id=participant.id,
                    name=participant.name,
                    church_or_school=participant.church_or_school,
                    grade=participant.grade,
                    participant_role=role if isinstance(role, str) else None,
                    phone=phone if isinstance(phone, str) else None,
                    registration_fee_paid=paid if isinstance(paid, bool) else None,
                    refund_requested=refund_requested if isinstance(refund_requested, bool) else None,
                    refund_status=refund_status if isinstance(refund_status, str) else None,
                    refund_reason=refund_reason if isinstance(refund_reason, str) else None,
                    refund_processed_by=refund_processed_by if isinstance(refund_processed_by, str) else None,
                    refund_processed_at=refund_processed_at if isinstance(refund_processed_at, str) else None,
                    ticket_status=ticket.status if ticket else None,
                )
            )
        return result
