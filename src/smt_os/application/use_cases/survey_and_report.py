from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from uuid import uuid4

from smt_os.application.ports.repositories import (
    CheckinRepository,
    EventRepository,
    ParticipantRepository,
    SurveyRepository,
)
from smt_os.domain.common.enums import CheckinType, SurveyQuestionType
from smt_os.domain.surveys.entities import SurveyQuestion, SurveyResponse


class SurveyEventNotFoundError(ValueError):
    pass


class SurveyValidationError(ValueError):
    pass


@dataclass(slots=True)
class SurveyQuestionInput:
    key: str
    label: str
    type: SurveyQuestionType
    required: bool = False
    options: list[str] = field(default_factory=list)
    sort_order: int = 0


@dataclass(slots=True)
class UpsertSurveyQuestionsCommand:
    event_id: str
    questions: list[SurveyQuestionInput]


@dataclass(slots=True)
class SubmitSurveyResponseCommand:
    event_id: str
    answers: dict[str, object]
    participant_id: str | None = None


@dataclass(slots=True)
class EventReportSummary:
    registered_count: int
    checked_in_count: int
    survey_response_count: int
    survey_response_rate: float
    survey_average_rating: float | None


class SurveyAndReportUseCase:
    def __init__(
        self,
        events: EventRepository,
        participants: ParticipantRepository,
        checkins: CheckinRepository,
        surveys: SurveyRepository,
    ) -> None:
        self._events = events
        self._participants = participants
        self._checkins = checkins
        self._surveys = surveys

    def _ensure_event(self, event_id: str) -> None:
        if self._events.get(event_id) is None:
            raise SurveyEventNotFoundError("event not found")

    def upsert_questions(self, command: UpsertSurveyQuestionsCommand) -> list[SurveyQuestion]:
        self._ensure_event(command.event_id)
        converted = [
            SurveyQuestion(
                id=str(uuid4()),
                event_id=command.event_id,
                key=item.key,
                label=item.label,
                type=item.type,
                required=item.required,
                options=item.options,
                sort_order=item.sort_order,
            )
            for item in command.questions
            if item.key.strip() and item.label.strip()
        ]
        self._surveys.replace_questions(command.event_id, converted)
        return converted

    def list_questions(self, event_id: str) -> list[SurveyQuestion]:
        return self._surveys.list_questions(event_id)

    def submit_response(self, command: SubmitSurveyResponseCommand) -> SurveyResponse:
        self._ensure_event(command.event_id)
        questions = self._surveys.list_questions(command.event_id)

        missing_required: list[str] = []
        for question in questions:
            if not question.required:
                continue
            value = command.answers.get(question.key)
            if value is None:
                missing_required.append(question.key)
                continue
            if isinstance(value, str) and not value.strip():
                missing_required.append(question.key)

        if missing_required:
            raise SurveyValidationError(f"missing required survey fields: {', '.join(missing_required)}")

        response = SurveyResponse(
            id=str(uuid4()),
            event_id=command.event_id,
            participant_id=command.participant_id,
            answers=command.answers,
        )
        self._surveys.save_response(response)
        return response

    def get_report_summary(self, event_id: str) -> EventReportSummary:
        self._ensure_event(event_id)

        participants = self._participants.list_by_event(event_id)
        participant_ids = {item.id for item in participants}
        checked_in = self._checkins.count_for_participants(
            event_id=event_id,
            participant_ids=participant_ids,
            checkin_type=CheckinType.ENTRY,
        )

        responses = self._surveys.list_responses(event_id)
        response_count = len(responses)

        rating_keys = {
            q.key
            for q in self._surveys.list_questions(event_id)
            if q.type == SurveyQuestionType.RATING
        }
        ratings: list[float] = []
        for response in responses:
            for key in rating_keys:
                value = response.answers.get(key)
                if isinstance(value, (int, float)):
                    ratings.append(float(value))
                elif isinstance(value, str) and value.strip().isdigit():
                    ratings.append(float(value.strip()))

        rate = 0.0
        if participants:
            rate = round((response_count / len(participants)) * 100, 2)

        avg_rating = round(mean(ratings), 2) if ratings else None

        return EventReportSummary(
            registered_count=len(participants),
            checked_in_count=checked_in,
            survey_response_count=response_count,
            survey_response_rate=rate,
            survey_average_rating=avg_rating,
        )
