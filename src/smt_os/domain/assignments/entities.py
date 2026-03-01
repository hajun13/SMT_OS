from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MealSlot:
    id: str
    event_id: str
    name: str
    capacity: int
    sort_order: int = 0


@dataclass(slots=True)
class MealAssignment:
    event_id: str
    participant_id: str
    slot_id: str


@dataclass(slots=True)
class GroupSlot:
    id: str
    event_id: str
    name: str
    capacity: int
    sort_order: int = 0


@dataclass(slots=True)
class GroupAssignment:
    event_id: str
    participant_id: str
    group_id: str
