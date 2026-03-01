from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smt_os.domain.common.enums import SurveyQuestionType


@dataclass(slots=True)
class SurveyQuestion:
    id: str
    event_id: str
    key: str
    label: str
    type: SurveyQuestionType
    required: bool = False
    options: list[str] = field(default_factory=list)
    sort_order: int = 0


@dataclass(slots=True)
class SurveyResponse:
    id: str
    event_id: str
    answers: dict[str, object]
    participant_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
