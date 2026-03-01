from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smt_os.domain.common.enums import FieldType


@dataclass(slots=True)
class RegistrationForm:
    id: str
    event_id: str
    version: int
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class FormField:
    id: str
    form_id: str
    key: str
    label: str
    type: FieldType
    required: bool = False
    options: list[str] = field(default_factory=list)
    sort_order: int = 0
