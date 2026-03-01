from __future__ import annotations

from dataclasses import dataclass

from smt_os.application.ports.repositories import ParticipantRepository
from smt_os.domain.participants.entities import Participant


class ParticipantNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class UpdateParticipantAnswersCommand:
    participant_id: str
    answers: dict[str, object]


class UpdateParticipantAnswersUseCase:
    def __init__(self, participants: ParticipantRepository) -> None:
        self._participants = participants

    def execute(self, command: UpdateParticipantAnswersCommand) -> Participant:
        participant = self._participants.get(command.participant_id)
        if participant is None:
            raise ParticipantNotFoundError("participant not found")

        merged_answers = dict(participant.answers)
        merged_answers.update(command.answers)
        updated = Participant(
            id=participant.id,
            event_id=participant.event_id,
            registration_id=participant.registration_id,
            name=participant.name,
            church_or_school=participant.church_or_school,
            grade=participant.grade,
            answers=merged_answers,
            created_at=participant.created_at,
        )
        self._participants.save(updated)
        return updated
