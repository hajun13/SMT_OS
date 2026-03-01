from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smt_os.domain.common.enums import CheckinType


@dataclass(slots=True)
class Checkin:
    id: str
    event_id: str
    participant_id: str
    type: CheckinType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
