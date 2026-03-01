from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from smt_os.domain.common.enums import (
    CheckinType,
    EventTemplate,
    FieldType,
    RegistrationKind,
    SurveyQuestionType,
)


class CreateEventRequest(BaseModel):
    org_id: str
    slug: str
    title: str
    template: EventTemplate
    start_at: datetime
    end_at: datetime
    capacity: int = Field(ge=0)


class RegisterParticipantRequest(BaseModel):
    event_id: str
    applicant_name: str
    participant_name: str
    kind: RegistrationKind = RegistrationKind.INDIVIDUAL
    church_or_school: str | None = None
    grade: str | None = None
    answers: dict[str, object] = Field(default_factory=dict)


class GroupParticipantRequest(BaseModel):
    participant_name: str
    church_or_school: str | None = None
    grade: str | None = None
    answers: dict[str, object] = Field(default_factory=dict)


class RegisterGroupRequest(BaseModel):
    applicant_name: str
    participants: list[GroupParticipantRequest]


class CheckinRequest(BaseModel):
    event_id: str
    token: str
    checkin_type: CheckinType = CheckinType.ENTRY


class CheckinByParticipantRequest(BaseModel):
    event_id: str
    participant_id: str
    checkin_type: CheckinType = CheckinType.ENTRY


class UpdateParticipantAnswersRequest(BaseModel):
    answers: dict[str, object]


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    account_type: str
    leader_role: str | None = None
    church_or_school: str | None = None
    team: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ApprovalDecisionRequest(BaseModel):
    approve: bool


class TeamLeadUpdateRequest(BaseModel):
    is_team_lead: bool


class RefundDecisionRequest(BaseModel):
    approve: bool


class ProfileImageUpdateRequest(BaseModel):
    image_data_url: str | None = None


class RegistrationFormFieldRequest(BaseModel):
    key: str
    label: str
    type: FieldType
    required: bool = False
    options: list[str] = Field(default_factory=list)
    sort_order: int = 0


class UpsertRegistrationFormRequest(BaseModel):
    fields: list[RegistrationFormFieldRequest]


class AssignmentSlotRequest(BaseModel):
    name: str
    capacity: int = Field(gt=0)
    sort_order: int = 0


class ConfigureMealSlotsRequest(BaseModel):
    slots: list[AssignmentSlotRequest]


class ConfigureGroupsRequest(BaseModel):
    groups: list[AssignmentSlotRequest]


class SurveyQuestionRequest(BaseModel):
    key: str
    label: str
    type: SurveyQuestionType
    required: bool = False
    options: list[str] = Field(default_factory=list)
    sort_order: int = 0


class UpsertSurveyQuestionsRequest(BaseModel):
    questions: list[SurveyQuestionRequest]


class SubmitSurveyResponseRequest(BaseModel):
    participant_id: str | None = None
    answers: dict[str, object]


class CreateMeetingRequest(BaseModel):
    org_id: str
    title: str
    started_at: datetime
    ended_at: datetime | None = None


class CreateMeetingNoteRequest(BaseModel):
    content: str


class CreateActionItemRequest(BaseModel):
    org_id: str
    title: str
    department: str | None = None
    due_at: datetime | None = None
    status: str = "open"
    event_id: str | None = None


class CreateTeamDocumentRequest(BaseModel):
    org_id: str
    title: str
    kind: str = "doc"
    content: str | None = None
    event_id: str | None = None
    version: int = Field(default=1, ge=1)
