from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from smt_os.application.ports.repositories import AssignmentRepository, EventRepository, ParticipantRepository
from smt_os.domain.assignments.entities import GroupAssignment, GroupSlot, MealAssignment, MealSlot


class AssignmentEventNotFoundError(ValueError):
    pass


class AssignmentCapacityError(ValueError):
    pass


@dataclass(slots=True)
class SlotInput:
    name: str
    capacity: int
    sort_order: int = 0


class AssignmentEngineUseCase:
    def __init__(
        self,
        events: EventRepository,
        participants: ParticipantRepository,
        assignments: AssignmentRepository,
    ) -> None:
        self._events = events
        self._participants = participants
        self._assignments = assignments

    def _ensure_event(self, event_id: str) -> None:
        if self._events.get(event_id) is None:
            raise AssignmentEventNotFoundError("event not found")

    def configure_meal_slots(self, event_id: str, slots: list[SlotInput]) -> list[MealSlot]:
        self._ensure_event(event_id)
        converted = [
            MealSlot(id=str(uuid4()), event_id=event_id, name=s.name, capacity=s.capacity, sort_order=s.sort_order)
            for s in slots
            if s.capacity > 0 and s.name.strip()
        ]
        self._assignments.replace_meal_slots(event_id, converted)
        return converted

    def list_meal_slots(self, event_id: str) -> list[MealSlot]:
        return self._assignments.list_meal_slots(event_id)

    def run_meal_assignment(self, event_id: str) -> list[MealAssignment]:
        self._ensure_event(event_id)
        slots = self._assignments.list_meal_slots(event_id)
        participants = self._participants.list_by_event(event_id)

        total_capacity = sum(slot.capacity for slot in slots)
        if len(participants) > total_capacity:
            raise AssignmentCapacityError("meal capacity is not enough")

        assignments: list[MealAssignment] = []
        cursor = 0
        usage = {slot.id: 0 for slot in slots}

        for participant in participants:
            while cursor < len(slots) and usage[slots[cursor].id] >= slots[cursor].capacity:
                cursor += 1
            if cursor >= len(slots):
                raise AssignmentCapacityError("meal capacity is not enough")
            slot = slots[cursor]
            usage[slot.id] += 1
            assignments.append(MealAssignment(event_id=event_id, participant_id=participant.id, slot_id=slot.id))

        self._assignments.replace_meal_assignments(event_id, assignments)
        return assignments

    def list_meal_assignments(self, event_id: str) -> list[MealAssignment]:
        return self._assignments.list_meal_assignments(event_id)

    def configure_groups(self, event_id: str, groups: list[SlotInput]) -> list[GroupSlot]:
        self._ensure_event(event_id)
        converted = [
            GroupSlot(id=str(uuid4()), event_id=event_id, name=s.name, capacity=s.capacity, sort_order=s.sort_order)
            for s in groups
            if s.capacity > 0 and s.name.strip()
        ]
        self._assignments.replace_group_slots(event_id, converted)
        return converted

    def list_groups(self, event_id: str) -> list[GroupSlot]:
        return self._assignments.list_group_slots(event_id)

    def run_group_assignment(self, event_id: str) -> list[GroupAssignment]:
        self._ensure_event(event_id)
        groups = self._assignments.list_group_slots(event_id)
        participants = self._participants.list_by_event(event_id)

        total_capacity = sum(group.capacity for group in groups)
        if len(participants) > total_capacity:
            raise AssignmentCapacityError("group capacity is not enough")

        assignments: list[GroupAssignment] = []
        cursor = 0
        usage = {group.id: 0 for group in groups}

        for participant in participants:
            while cursor < len(groups) and usage[groups[cursor].id] >= groups[cursor].capacity:
                cursor += 1
            if cursor >= len(groups):
                raise AssignmentCapacityError("group capacity is not enough")
            group = groups[cursor]
            usage[group.id] += 1
            assignments.append(GroupAssignment(event_id=event_id, participant_id=participant.id, group_id=group.id))

        self._assignments.replace_group_assignments(event_id, assignments)
        return assignments

    def list_group_assignments(self, event_id: str) -> list[GroupAssignment]:
        return self._assignments.list_group_assignments(event_id)
