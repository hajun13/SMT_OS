from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from smt_os.application.ports.repositories import EventRepository, TeamRepository
from smt_os.domain.team.entities import ActionItem, Meeting, MeetingNote, TeamDocument


class TeamEventNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class CreateMeetingCommand:
    org_id: str
    title: str
    started_at: datetime
    ended_at: datetime | None = None


@dataclass(slots=True)
class CreateMeetingNoteCommand:
    meeting_id: str
    content: str


@dataclass(slots=True)
class CreateActionItemCommand:
    org_id: str
    title: str
    department: str | None = None
    due_at: datetime | None = None
    status: str = "open"
    event_id: str | None = None


@dataclass(slots=True)
class CreateDocumentCommand:
    org_id: str
    title: str
    kind: str = "doc"
    content: str | None = None
    event_id: str | None = None
    version: int = 1


class TeamOSUseCase:
    def __init__(self, events: EventRepository, team: TeamRepository) -> None:
        self._events = events
        self._team = team

    def _ensure_event(self, event_id: str | None) -> None:
        if event_id is None:
            return
        if self._events.get(event_id) is None:
            raise TeamEventNotFoundError("event not found")

    def create_meeting(self, command: CreateMeetingCommand) -> Meeting:
        meeting = Meeting(
            id=str(uuid4()),
            org_id=command.org_id,
            title=command.title,
            started_at=command.started_at,
            ended_at=command.ended_at,
        )
        self._team.save_meeting(meeting)
        return meeting

    def list_meetings(self, org_id: str) -> list[Meeting]:
        return self._team.list_meetings(org_id)

    def add_meeting_note(self, command: CreateMeetingNoteCommand) -> MeetingNote:
        note = MeetingNote(
            id=str(uuid4()),
            meeting_id=command.meeting_id,
            content=command.content,
        )
        self._team.save_meeting_note(note)
        return note

    def list_meeting_notes(self, meeting_id: str) -> list[MeetingNote]:
        return self._team.list_meeting_notes(meeting_id)

    def create_action_item(self, command: CreateActionItemCommand) -> ActionItem:
        self._ensure_event(command.event_id)
        item = ActionItem(
            id=str(uuid4()),
            org_id=command.org_id,
            title=command.title,
            department=command.department,
            due_at=command.due_at,
            status=command.status,
            event_id=command.event_id,
        )
        self._team.save_action_item(item)
        return item

    def list_action_items(self, org_id: str, status: str | None = None) -> list[ActionItem]:
        return self._team.list_action_items(org_id, status=status)

    def create_document(self, command: CreateDocumentCommand) -> TeamDocument:
        self._ensure_event(command.event_id)
        # participant_info는 이벤트별 최신 1건만 유지한다.
        if command.kind == "participant_info" and command.event_id:
            existing = next(
                (
                    doc
                    for doc in self._team.list_documents(command.org_id, kind="participant_info")
                    if doc.event_id == command.event_id
                ),
                None,
            )
            if existing is not None:
                doc = TeamDocument(
                    id=existing.id,
                    org_id=command.org_id,
                    title=command.title,
                    kind=command.kind,
                    content=command.content,
                    event_id=command.event_id,
                    version=max(existing.version + 1, command.version),
                )
                self._team.save_document(doc)
                return doc

        doc = TeamDocument(
            id=str(uuid4()),
            org_id=command.org_id,
            title=command.title,
            kind=command.kind,
            content=command.content,
            event_id=command.event_id,
            version=command.version,
        )
        self._team.save_document(doc)
        return doc

    def list_documents(self, org_id: str, kind: str | None = None) -> list[TeamDocument]:
        return self._team.list_documents(org_id, kind=kind)
