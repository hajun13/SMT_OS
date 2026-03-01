from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smt_os.domain.common.enums import RegistrationKind


@dataclass(slots=True)
class Registration:
    id: str
    event_id: str
    kind: RegistrationKind
    applicant_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Participant:
    id: str
    event_id: str
    registration_id: str
    name: str
    church_or_school: str | None = None
    grade: str | None = None
    answers: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Ticket:
    id: str
    participant_id: str
    token: str
    status: str = "issued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
