from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from uuid import uuid4

from smt_os.application.ports.repositories import (
    EventRepository,
    ParticipantRepository,
    RegistrationFormRepository,
    RegistrationRepository,
    TicketRepository,
)
from smt_os.domain.common.enums import RegistrationKind
from smt_os.domain.participants.entities import Participant, Registration, Ticket


class EventNotFoundError(ValueError):
    pass


class RegistrationValidationError(ValueError):
    pass


@dataclass(slots=True)
class RegisterParticipantCommand:
    event_id: str
    applicant_name: str
    participant_name: str
    kind: RegistrationKind = RegistrationKind.INDIVIDUAL
    church_or_school: str | None = None
    grade: str | None = None
    answers: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GroupParticipantInput:
    participant_name: str
    church_or_school: str | None = None
    grade: str | None = None
    answers: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RegisterGroupCommand:
    event_id: str
    applicant_name: str
    participants: list[GroupParticipantInput]


@dataclass(slots=True)
class RegisterParticipantResult:
    registration: Registration
    participant: Participant
    ticket: Ticket


@dataclass(slots=True)
class GroupParticipantResult:
    participant: Participant
    ticket: Ticket


@dataclass(slots=True)
class RegisterGroupResult:
    registration: Registration
    participants: list[GroupParticipantResult]


class RegisterParticipantUseCase:
    def __init__(
        self,
        events: EventRepository,
        registrations: RegistrationRepository,
        participants: ParticipantRepository,
        tickets: TicketRepository,
        forms: RegistrationFormRepository,
    ) -> None:
        self._events = events
        self._registrations = registrations
        self._participants = participants
        self._tickets = tickets
        self._forms = forms

    def _ensure_event(self, event_id: str) -> None:
        if self._events.get(event_id) is None:
            raise EventNotFoundError("event not found")

    def _validate_answers(self, event_id: str, answers: dict[str, object]) -> None:
        active_form = self._forms.get_active(event_id)
        if active_form is None:
            self._validate_role_phone(answers)
            return

        fields = self._forms.list_fields(active_form.id)
        missing_required: list[str] = []
        for field in fields:
            if not field.required:
                continue
            value = answers.get(field.key)
            if value is None:
                missing_required.append(field.key)
                continue
            if isinstance(value, str) and not value.strip():
                missing_required.append(field.key)
            if isinstance(value, list) and len(value) == 0:
                missing_required.append(field.key)

        if missing_required:
            joined = ", ".join(missing_required)
            raise RegistrationValidationError(f"missing required fields: {joined}")
        self._validate_role_phone(answers)

    def _validate_role_phone(self, answers: dict[str, object]) -> None:
        role = answers.get("participant_role")
        if not isinstance(role, str):
            return
        if role not in {"teacher", "evangelist", "pastor"}:
            return
        phone = answers.get("phone")
        if not isinstance(phone, str) or not phone.strip():
            raise RegistrationValidationError("phone is required for teacher/evangelist/pastor")

    def _create_registration(self, event_id: str, applicant_name: str, kind: RegistrationKind) -> Registration:
        registration = Registration(
            id=str(uuid4()),
            event_id=event_id,
            kind=kind,
            applicant_name=applicant_name,
        )
        self._registrations.save(registration)
        return registration

    def _create_participant_with_ticket(
        self,
        event_id: str,
        registration_id: str,
        participant_name: str,
        church_or_school: str | None,
        grade: str | None,
        answers: dict[str, object],
    ) -> GroupParticipantResult:
        participant = Participant(
            id=str(uuid4()),
            event_id=event_id,
            registration_id=registration_id,
            name=participant_name,
            church_or_school=church_or_school,
            grade=grade,
            answers=answers,
        )
        ticket = Ticket(
            id=str(uuid4()),
            participant_id=participant.id,
            token=secrets.token_urlsafe(24),
        )
        self._participants.save(participant)
        self._tickets.save(ticket)
        return GroupParticipantResult(participant=participant, ticket=ticket)

    def execute(self, command: RegisterParticipantCommand) -> RegisterParticipantResult:
        self._ensure_event(command.event_id)
        self._validate_answers(command.event_id, command.answers)

        registration = self._create_registration(
            event_id=command.event_id,
            applicant_name=command.applicant_name,
            kind=command.kind,
        )

        result = self._create_participant_with_ticket(
            event_id=command.event_id,
            registration_id=registration.id,
            participant_name=command.participant_name,
            church_or_school=command.church_or_school,
            grade=command.grade,
            answers=command.answers,
        )

        return RegisterParticipantResult(
            registration=registration,
            participant=result.participant,
            ticket=result.ticket,
        )

    def execute_group(self, command: RegisterGroupCommand) -> RegisterGroupResult:
        self._ensure_event(command.event_id)
        if not command.participants:
            raise RegistrationValidationError("participants is required")

        for item in command.participants:
            if not item.participant_name.strip():
                raise RegistrationValidationError("participant_name is required")
            self._validate_answers(command.event_id, item.answers)

        registration = self._create_registration(
            event_id=command.event_id,
            applicant_name=command.applicant_name,
            kind=RegistrationKind.GROUP,
        )

        created: list[GroupParticipantResult] = []
        for item in command.participants:
            created.append(
                self._create_participant_with_ticket(
                    event_id=command.event_id,
                    registration_id=registration.id,
                    participant_name=item.participant_name,
                    church_or_school=item.church_or_school,
                    grade=item.grade,
                    answers=item.answers,
                )
            )

        return RegisterGroupResult(registration=registration, participants=created)
