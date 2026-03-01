from __future__ import annotations

from smt_os.application.ports.repositories import (
    AssignmentRepository,
    CheckinRepository,
    EventRepository,
    ParticipantRepository,
    RegistrationFormRepository,
    RegistrationRepository,
    SurveyRepository,
    TeamRepository,
    TicketRepository,
)
from smt_os.domain.assignments.entities import GroupAssignment, GroupSlot, MealAssignment, MealSlot
from smt_os.domain.checkins.entities import Checkin
from smt_os.domain.common.enums import CheckinType
from smt_os.domain.events.entities import Event
from smt_os.domain.forms.entities import FormField, RegistrationForm
from smt_os.domain.participants.entities import Participant, Registration, Ticket
from smt_os.domain.surveys.entities import SurveyQuestion, SurveyResponse
from smt_os.domain.team.entities import ActionItem, Meeting, MeetingNote, TeamDocument


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._items: dict[str, Event] = {}

    def save(self, event: Event) -> None:
        self._items[event.id] = event

    def get(self, event_id: str) -> Event | None:
        return self._items.get(event_id)

    def get_by_slug(self, slug: str) -> Event | None:
        for event in self._items.values():
            if event.slug == slug:
                return event
        return None

    def list(self) -> list[Event]:
        return list(self._items.values())

    def delete(self, event_id: str) -> Event | None:
        return self._items.pop(event_id, None)


class InMemoryRegistrationRepository(RegistrationRepository):
    def __init__(self) -> None:
        self._items: dict[str, Registration] = {}

    def save(self, registration: Registration) -> None:
        self._items[registration.id] = registration


class InMemoryParticipantRepository(ParticipantRepository):
    def __init__(self) -> None:
        self._items: dict[str, Participant] = {}

    def save(self, participant: Participant) -> None:
        self._items[participant.id] = participant

    def get(self, participant_id: str) -> Participant | None:
        return self._items.get(participant_id)

    def list_by_event(
        self,
        event_id: str,
        church_or_school: str | None = None,
        grade: str | None = None,
        name_query: str | None = None,
    ) -> list[Participant]:
        result = [item for item in self._items.values() if item.event_id == event_id]
        if church_or_school:
            result = [item for item in result if item.church_or_school == church_or_school]
        if grade:
            result = [item for item in result if item.grade == grade]
        if name_query:
            q = name_query.strip().lower()
            result = [item for item in result if q in item.name.lower()]
        return result


class InMemoryTicketRepository(TicketRepository):
    def __init__(self) -> None:
        self._items: dict[str, Ticket] = {}
        self._token_index: dict[str, str] = {}
        self._participant_index: dict[str, str] = {}

    def save(self, ticket: Ticket) -> None:
        self._items[ticket.id] = ticket
        self._token_index[ticket.token] = ticket.id
        self._participant_index[ticket.participant_id] = ticket.id

    def find_by_token(self, token: str) -> Ticket | None:
        ticket_id = self._token_index.get(token)
        if ticket_id is None:
            return None
        return self._items.get(ticket_id)

    def find_by_participant_id(self, participant_id: str) -> Ticket | None:
        ticket_id = self._participant_index.get(participant_id)
        if ticket_id is None:
            return None
        return self._items.get(ticket_id)


class InMemoryCheckinRepository(CheckinRepository):
    def __init__(self) -> None:
        self._items: dict[str, Checkin] = {}
        self._index: set[tuple[str, str, CheckinType]] = set()

    def save(self, checkin: Checkin) -> None:
        self._items[checkin.id] = checkin
        self._index.add((checkin.event_id, checkin.participant_id, checkin.type))

    def exists(self, event_id: str, participant_id: str, checkin_type: CheckinType) -> bool:
        return (event_id, participant_id, checkin_type) in self._index

    def count_for_participants(
        self,
        event_id: str,
        participant_ids: set[str],
        checkin_type: CheckinType,
    ) -> int:
        if not participant_ids:
            return 0
        return sum(
            1
            for item in self._items.values()
            if item.event_id == event_id
            and item.type == checkin_type
            and item.participant_id in participant_ids
        )


class InMemoryRegistrationFormRepository(RegistrationFormRepository):
    def __init__(self) -> None:
        self._forms: dict[str, RegistrationForm] = {}
        self._active_form_by_event: dict[str, str] = {}
        self._fields_by_form: dict[str, list[FormField]] = {}

    def save(self, form: RegistrationForm) -> None:
        self._forms[form.id] = form
        if form.is_active:
            self._active_form_by_event[form.event_id] = form.id

    def get_active(self, event_id: str) -> RegistrationForm | None:
        form_id = self._active_form_by_event.get(event_id)
        if form_id is None:
            return None
        return self._forms.get(form_id)

    def replace_fields(self, form_id: str, fields: list[FormField]) -> None:
        self._fields_by_form[form_id] = sorted(fields, key=lambda x: x.sort_order)

    def list_fields(self, form_id: str) -> list[FormField]:
        return list(self._fields_by_form.get(form_id, []))


class InMemoryAssignmentRepository(AssignmentRepository):
    def __init__(self) -> None:
        self._meal_slots: dict[str, list[MealSlot]] = {}
        self._meal_assignments: dict[str, list[MealAssignment]] = {}
        self._group_slots: dict[str, list[GroupSlot]] = {}
        self._group_assignments: dict[str, list[GroupAssignment]] = {}

    def replace_meal_slots(self, event_id: str, slots: list[MealSlot]) -> None:
        self._meal_slots[event_id] = sorted(slots, key=lambda x: x.sort_order)

    def list_meal_slots(self, event_id: str) -> list[MealSlot]:
        return list(self._meal_slots.get(event_id, []))

    def replace_meal_assignments(self, event_id: str, items: list[MealAssignment]) -> None:
        self._meal_assignments[event_id] = list(items)

    def list_meal_assignments(self, event_id: str) -> list[MealAssignment]:
        return list(self._meal_assignments.get(event_id, []))

    def replace_group_slots(self, event_id: str, groups: list[GroupSlot]) -> None:
        self._group_slots[event_id] = sorted(groups, key=lambda x: x.sort_order)

    def list_group_slots(self, event_id: str) -> list[GroupSlot]:
        return list(self._group_slots.get(event_id, []))

    def replace_group_assignments(self, event_id: str, items: list[GroupAssignment]) -> None:
        self._group_assignments[event_id] = list(items)

    def list_group_assignments(self, event_id: str) -> list[GroupAssignment]:
        return list(self._group_assignments.get(event_id, []))


class InMemorySurveyRepository(SurveyRepository):
    def __init__(self) -> None:
        self._questions_by_event: dict[str, list[SurveyQuestion]] = {}
        self._responses_by_event: dict[str, list[SurveyResponse]] = {}

    def replace_questions(self, event_id: str, questions: list[SurveyQuestion]) -> None:
        self._questions_by_event[event_id] = sorted(questions, key=lambda x: x.sort_order)

    def list_questions(self, event_id: str) -> list[SurveyQuestion]:
        return list(self._questions_by_event.get(event_id, []))

    def save_response(self, response: SurveyResponse) -> None:
        bucket = self._responses_by_event.setdefault(response.event_id, [])
        bucket.append(response)

    def list_responses(self, event_id: str) -> list[SurveyResponse]:
        return list(self._responses_by_event.get(event_id, []))


class InMemoryTeamRepository(TeamRepository):
    def __init__(self) -> None:
        self._meetings: dict[str, Meeting] = {}
        self._meeting_notes: dict[str, list[MeetingNote]] = {}
        self._action_items: dict[str, ActionItem] = {}
        self._documents: dict[str, TeamDocument] = {}

    def save_meeting(self, meeting: Meeting) -> None:
        self._meetings[meeting.id] = meeting

    def list_meetings(self, org_id: str) -> list[Meeting]:
        items = [m for m in self._meetings.values() if m.org_id == org_id]
        return sorted(items, key=lambda x: x.started_at, reverse=True)

    def delete_meeting(self, meeting_id: str) -> bool:
        removed = self._meetings.pop(meeting_id, None)
        self._meeting_notes.pop(meeting_id, None)
        return removed is not None

    def save_meeting_note(self, note: MeetingNote) -> None:
        bucket = self._meeting_notes.setdefault(note.meeting_id, [])
        bucket.append(note)

    def list_meeting_notes(self, meeting_id: str) -> list[MeetingNote]:
        return list(self._meeting_notes.get(meeting_id, []))

    def save_action_item(self, item: ActionItem) -> None:
        self._action_items[item.id] = item

    def list_action_items(self, org_id: str, status: str | None = None) -> list[ActionItem]:
        items = [a for a in self._action_items.values() if a.org_id == org_id]
        if status:
            items = [a for a in items if a.status == status]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def delete_action_item(self, action_item_id: str) -> bool:
        return self._action_items.pop(action_item_id, None) is not None

    def save_document(self, doc: TeamDocument) -> None:
        self._documents[doc.id] = doc

    def list_documents(self, org_id: str, kind: str | None = None) -> list[TeamDocument]:
        items = [d for d in self._documents.values() if d.org_id == org_id]
        if kind:
            items = [d for d in items if d.kind == kind]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def delete_document(self, document_id: str) -> bool:
        return self._documents.pop(document_id, None) is not None
