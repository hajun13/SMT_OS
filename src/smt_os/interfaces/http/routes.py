from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, UploadFile
from fastapi.responses import Response

from smt_os.application.use_cases.assignment_engine import (
    AssignmentCapacityError,
    AssignmentEngineUseCase,
    AssignmentEventNotFoundError,
    SlotInput,
)
from smt_os.application.use_cases.checkin_by_token import (
    CheckinByTokenCommand,
    CheckinByTokenUseCase,
    DuplicateCheckinError,
    InvalidTicketError,
)
from smt_os.application.use_cases.create_event import CreateEventCommand, CreateEventUseCase
from smt_os.application.use_cases.delete_event import DeleteEventNotFoundError, DeleteEventUseCase
from smt_os.application.use_cases.get_event_dashboard import GetEventDashboardQuery, GetEventDashboardUseCase
from smt_os.application.use_cases.get_public_event import EventNotFoundBySlugError, GetPublicEventUseCase
from smt_os.application.use_cases.get_public_registration_form import GetPublicRegistrationFormUseCase
from smt_os.application.use_cases.get_public_ticket import GetPublicTicketUseCase, TicketNotFoundError
from smt_os.application.use_cases.list_events import ListEventsUseCase
from smt_os.application.use_cases.list_participants import ListParticipantsQuery, ListParticipantsUseCase
from smt_os.application.use_cases.register_participant import (
    EventNotFoundError,
    GroupParticipantInput,
    RegisterGroupCommand,
    RegisterParticipantCommand,
    RegisterParticipantUseCase,
    RegistrationValidationError,
)
from smt_os.application.use_cases.survey_and_report import (
    SubmitSurveyResponseCommand,
    SurveyAndReportUseCase,
    SurveyEventNotFoundError,
    SurveyQuestionInput,
    SurveyValidationError,
    UpsertSurveyQuestionsCommand,
)
from smt_os.application.use_cases.team_os import (
    CreateActionItemCommand,
    CreateDocumentCommand,
    CreateMeetingCommand,
    CreateMeetingNoteCommand,
    TeamEventNotFoundError,
    TeamOSUseCase,
)
from smt_os.application.use_cases.update_participant_answers import (
    ParticipantNotFoundError,
    UpdateParticipantAnswersCommand,
    UpdateParticipantAnswersUseCase,
)
from smt_os.application.use_cases.upsert_registration_form import (
    FieldInput,
    RegistrationFormEventNotFoundError,
    UpsertRegistrationFormCommand,
    UpsertRegistrationFormUseCase,
)
from smt_os.domain.events.entities import Event
from smt_os.interfaces.http.auth import require_roles, require_team_lead
from smt_os.interfaces.http.auth_store import (
    decide_user,
    get_profile_images_by_name,
    get_ministry_users,
    get_pending_users,
    get_user_by_token,
    is_super_admin_user,
    login as auth_login,
    logout as auth_logout,
    set_profile_image,
    set_team_lead,
    signup as auth_signup,
    to_public_user,
)
from smt_os.interfaces.http.schemas import (
    ApprovalDecisionRequest,
    CheckinByParticipantRequest,
    CheckinRequest,
    ConfigureGroupsRequest,
    ConfigureMealSlotsRequest,
    CreateActionItemRequest,
    CreateEventRequest,
    CreateMeetingNoteRequest,
    CreateMeetingRequest,
    CreateTeamDocumentRequest,
    RegisterGroupRequest,
    RegisterParticipantRequest,
    LoginRequest,
    ProfileImageUpdateRequest,
    RefundDecisionRequest,
    SignupRequest,
    TeamLeadUpdateRequest,
    SubmitSurveyResponseRequest,
    UpdateParticipantAnswersRequest,
    UpsertRegistrationFormRequest,
    UpsertSurveyQuestionsRequest,
)


@dataclass(slots=True)
class Services:
    create_event: CreateEventUseCase
    delete_event: DeleteEventUseCase
    list_events: ListEventsUseCase
    register_participant: RegisterParticipantUseCase
    checkin_by_token: CheckinByTokenUseCase
    get_dashboard: GetEventDashboardUseCase
    list_participants: ListParticipantsUseCase
    get_public_ticket: GetPublicTicketUseCase
    get_public_event: GetPublicEventUseCase
    upsert_registration_form: UpsertRegistrationFormUseCase
    get_public_registration_form: GetPublicRegistrationFormUseCase
    assignment_engine: AssignmentEngineUseCase
    survey_and_report: SurveyAndReportUseCase
    team_os: TeamOSUseCase
    update_participant_answers: UpdateParticipantAnswersUseCase


ORG_CHART_MEMBERS: list[dict[str, object]] = [
    {
        "team": "운영팀",
        "members": [
            {"role": "운영팀장", "name": "정하준"},
            {"role": "운영 부팀장", "name": "임의창"},
            {"role": "총무", "name": "이현호"},
        ],
    },
    {
        "team": "교육팀",
        "members": [
            {"role": "교육팀장", "name": "은성진"},
            {"role": "교육팀원", "name": "최지명"},
            {"role": "교육팀원", "name": "정성희"},
        ],
    },
    {
        "team": "기획팀",
        "members": [
            {"role": "기획팀장", "name": "이한빛"},
            {"role": "기획팀원", "name": "임태훈"},
            {"role": "기획팀원", "name": "이정서"},
            {"role": "기획팀원", "name": "서한임"},
        ],
    },
    {
        "team": "생활팀",
        "members": [
            {"role": "생활팀장", "name": "김유민"},
            {"role": "생활팀원", "name": "권현웅"},
            {"role": "생활팀원", "name": "김지원"},
            {"role": "생활팀원", "name": "정연우"},
        ],
    },
    {
        "team": "홍보팀",
        "members": [
            {"role": "홍보팀장", "name": "임예찬"},
            {"role": "홍보팀원", "name": "정예인"},
            {"role": "홍보팀원", "name": "김명은"},
        ],
    },
    {
        "team": "메딕/미디어",
        "members": [
            {"role": "메딕/미디어", "name": "이해언"},
        ],
    },
]


def _normalize_answers(
    answers: dict[str, object], church_or_school: str | None, grade: str | None
) -> dict[str, object]:
    merged = dict(answers)
    if grade and not merged.get("grade"):
        merged["grade"] = grade
    if church_or_school and not merged.get("church_or_school"):
        merged["church_or_school"] = church_or_school
    return merged


def build_router(services: Services) -> APIRouter:
    router = APIRouter()

    def _require_approver(authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="authentication is required")
        token = authorization.replace("Bearer ", "").strip()
        me_user = get_user_by_token(token)
        if me_user is None:
            raise HTTPException(status_code=401, detail="invalid session")
        if not me_user.can_approve or not is_super_admin_user(me_user):
            raise HTTPException(status_code=403, detail="super admin permission required")
        return token

    def _require_team_lead_user(authorization: str | None) -> tuple[str, str]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="authentication is required")
        token = authorization.replace("Bearer ", "").strip()
        user = get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid session")
        if user.account_type != "ministry" or user.status != "approved" or not user.is_team_lead:
            raise HTTPException(status_code=403, detail="team lead permission required")
        return user.id, user.name

    def _find_event(event_id: str) -> Event:
        event = next((item for item in services.list_events.execute() if item.id == event_id), None)
        if event is None:
            raise HTTPException(status_code=404, detail="event not found")
        return event

    @router.post("/api/auth/signup")
    def signup(payload: SignupRequest) -> dict[str, object]:
        if payload.account_type not in {"ministry", "leader"}:
            raise HTTPException(status_code=422, detail="students cannot sign up")
        try:
            user = auth_signup(
                email=payload.email,
                password=payload.password,
                name=payload.name,
                account_type=payload.account_type,  # type: ignore[arg-type]
                leader_role=payload.leader_role,
                church_or_school=payload.church_or_school,
                team=payload.team,
            )
        except ValueError as exc:
            detail = str(exc)
            if "rate limit" in detail.lower():
                raise HTTPException(status_code=429, detail=detail) from exc
            raise HTTPException(status_code=422, detail=detail) from exc
        return {"user": to_public_user(user)}

    @router.post("/api/auth/login")
    def login(payload: LoginRequest) -> dict[str, object]:
        try:
            token, user = auth_login(payload.email, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"token": token, "user": to_public_user(user)}

    @router.post("/api/auth/logout")
    def logout(authorization: str | None = Header(default=None, alias="authorization")) -> dict[str, str]:
        if not authorization or not authorization.startswith("Bearer "):
            return {"status": "ok"}
        token = authorization.replace("Bearer ", "").strip()
        auth_logout(token)
        return {"status": "ok"}

    @router.get("/api/auth/me")
    def me(authorization: str | None = Header(default=None, alias="authorization")) -> dict[str, object]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="authentication is required")
        token = authorization.replace("Bearer ", "").strip()
        user = get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid session")
        return {"user": to_public_user(user)}

    @router.patch("/api/auth/me/profile-image")
    def patch_my_profile_image(
        payload: ProfileImageUpdateRequest,
        authorization: str | None = Header(default=None, alias="authorization"),
    ) -> dict[str, object]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="authentication is required")
        token = authorization.replace("Bearer ", "").strip()
        user = get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid session")

        image_data_url = payload.image_data_url.strip() if isinstance(payload.image_data_url, str) else ""
        if image_data_url and not image_data_url.startswith("data:image/"):
            raise HTTPException(status_code=422, detail="invalid image format")
        if len(image_data_url) > 3_000_000:
            raise HTTPException(status_code=422, detail="image is too large")

        updated = set_profile_image(user.id, image_data_url or None)
        return {"user": to_public_user(updated)}

    @router.get("/api/auth/approvals")
    def list_pending_approvals(authorization: str | None = Header(default=None, alias="authorization")) -> list[dict[str, object]]:
        _require_approver(authorization)
        return [to_public_user(user) for user in get_pending_users()]

    @router.post("/api/auth/approvals/{user_id}")
    def decide_pending_approval(
        user_id: str,
        payload: ApprovalDecisionRequest,
        authorization: str | None = Header(default=None, alias="authorization"),
    ) -> dict[str, object]:
        _require_approver(authorization)
        try:
            user = decide_user(user_id, payload.approve)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"user": to_public_user(user)}

    @router.get("/api/auth/ministry-users")
    def list_ministry_users(authorization: str | None = Header(default=None, alias="authorization")) -> list[dict[str, object]]:
        _require_approver(authorization)
        return [to_public_user(user) for user in get_ministry_users()]

    @router.patch("/api/auth/ministry-users/{user_id}/team-lead")
    def patch_team_lead(
        user_id: str,
        payload: TeamLeadUpdateRequest,
        authorization: str | None = Header(default=None, alias="authorization"),
    ) -> dict[str, object]:
        _require_approver(authorization)
        try:
            user = set_team_lead(user_id, payload.is_team_lead)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"user": to_public_user(user)}

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "bounded_context": "event_os"}

    @router.post("/api/events")
    def create_event(
        payload: CreateEventRequest,
        _: str = Depends(require_roles("org_admin", "event_admin")),
    ) -> dict[str, object]:
        event = services.create_event.execute(
            CreateEventCommand(
                org_id=payload.org_id,
                slug=payload.slug,
                title=payload.title,
                template=payload.template,
                start_at=payload.start_at,
                end_at=payload.end_at,
                capacity=payload.capacity,
            )
        )
        return {
            "id": event.id,
            "slug": event.slug,
            "title": event.title,
            "template": event.template.value,
            "modules": {
                "seats": event.modules.seats,
                "meals": event.modules.meals,
                "groups": event.modules.groups,
                "activities": event.modules.activities,
                "lodging": event.modules.lodging,
                "buses": event.modules.buses,
            },
        }

    @router.delete("/api/events/{event_id}")
    def delete_event(
        event_id: str,
        _: str = Depends(require_team_lead()),
    ) -> dict[str, str]:
        try:
            deleted = services.delete_event.execute(event_id)
        except DeleteEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": deleted.id, "title": deleted.title}

    @router.get("/api/events")
    def list_events(
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        events = services.list_events.execute()
        return [
            {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "template": event.template.value,
            }
            for event in events
        ]

    @router.put("/api/events/{event_id}/registration-form")
    def upsert_registration_form(
        event_id: str,
        payload: UpsertRegistrationFormRequest,
        _: str = Depends(require_roles("org_admin", "event_admin")),
    ) -> dict[str, str | int]:
        try:
            form = services.upsert_registration_form.execute(
                UpsertRegistrationFormCommand(
                    event_id=event_id,
                    fields=[
                        FieldInput(
                            key=item.key,
                            label=item.label,
                            type=item.type,
                            required=item.required,
                            options=item.options,
                            sort_order=item.sort_order,
                        )
                        for item in payload.fields
                    ],
                )
            )
        except RegistrationFormEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {"form_id": form.id, "event_id": form.event_id, "version": form.version}

    @router.put("/api/events/{event_id}/survey/questions")
    def upsert_survey_questions(
        event_id: str,
        payload: UpsertSurveyQuestionsRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> list[dict[str, object]]:
        try:
            questions = services.survey_and_report.upsert_questions(
                UpsertSurveyQuestionsCommand(
                    event_id=event_id,
                    questions=[
                        SurveyQuestionInput(
                            key=item.key,
                            label=item.label,
                            type=item.type,
                            required=item.required,
                            options=item.options,
                            sort_order=item.sort_order,
                        )
                        for item in payload.questions
                    ],
                )
            )
        except SurveyEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return [
            {
                "id": q.id,
                "key": q.key,
                "label": q.label,
                "type": q.type.value,
                "required": q.required,
                "options": q.options,
                "sort_order": q.sort_order,
            }
            for q in questions
        ]

    @router.get("/api/public/events/{slug}")
    def get_public_event(slug: str) -> dict[str, object]:
        try:
            event = services.get_public_event.execute(slug)
        except EventNotFoundBySlugError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {
            "id": event.id,
            "slug": event.slug,
            "title": event.title,
            "template": event.template,
            "start_at": event.start_at,
            "end_at": event.end_at,
            "capacity": event.capacity,
        }

    @router.get("/api/public/org-chart")
    def get_public_org_chart() -> list[dict[str, object]]:
        names: list[str] = []
        for team in ORG_CHART_MEMBERS:
            for member in team["members"]:  # type: ignore[index]
                names.append(str(member["name"]))  # type: ignore[index]

        images = get_profile_images_by_name(names)
        result: list[dict[str, object]] = []
        for team in ORG_CHART_MEMBERS:
            members = []
            for member in team["members"]:  # type: ignore[index]
                name = str(member["name"])  # type: ignore[index]
                members.append(
                    {
                        "role": member["role"],  # type: ignore[index]
                        "name": name,
                        "photo_url": images.get(name),
                    }
                )
            result.append({"team": team["team"], "members": members})
        return result

    @router.get("/api/public/events/{event_id}/registration-form")
    def get_public_registration_form(event_id: str) -> list[dict[str, object]]:
        fields = services.get_public_registration_form.execute(event_id)
        return [
            {
                "key": field.key,
                "label": field.label,
                "type": field.type,
                "required": field.required,
                "options": field.options,
                "sort_order": field.sort_order,
            }
            for field in fields
        ]

    @router.get("/api/public/events/{event_id}/participant-info")
    def get_public_participant_info(event_id: str) -> dict[str, str]:
        event = _find_event(event_id)
        docs = services.team_os.list_documents(event.org_id, kind="participant_info")
        target = next((doc for doc in docs if doc.event_id == event_id), None)
        if target is None:
            return {"title": "행사 안내", "content": "장소 안내와 준비물을 확인하고 등록을 진행해 주세요."}
        return {
            "title": target.title,
            "content": target.content or "",
        }

    @router.get("/api/public/events/{event_id}/survey/questions")
    def get_public_survey_questions(event_id: str) -> list[dict[str, object]]:
        questions = services.survey_and_report.list_questions(event_id)
        return [
            {
                "key": q.key,
                "label": q.label,
                "type": q.type.value,
                "required": q.required,
                "options": q.options,
                "sort_order": q.sort_order,
            }
            for q in questions
        ]

    @router.post("/api/public/events/{event_id}/survey/responses")
    def submit_survey_response(event_id: str, payload: SubmitSurveyResponseRequest) -> dict[str, str]:
        try:
            saved = services.survey_and_report.submit_response(
                SubmitSurveyResponseCommand(
                    event_id=event_id,
                    participant_id=payload.participant_id,
                    answers=payload.answers,
                )
            )
        except SurveyEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SurveyValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {"response_id": saved.id}

    @router.post("/api/participants/register")
    def register_participant(payload: RegisterParticipantRequest) -> dict[str, object]:
        try:
            result = services.register_participant.execute(
                RegisterParticipantCommand(
                    event_id=payload.event_id,
                    applicant_name=payload.applicant_name,
                    participant_name=payload.participant_name,
                    kind=payload.kind,
                    church_or_school=payload.church_or_school,
                    grade=payload.grade,
                    answers=_normalize_answers(payload.answers, payload.church_or_school, payload.grade),
                )
            )
        except EventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RegistrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {
            "registration_id": result.registration.id,
            "participant_id": result.participant.id,
            "ticket": {
                "token": result.ticket.token,
                "status": result.ticket.status,
            },
        }

    @router.post("/api/events/{event_id}/registrations/group")
    def register_group(
        event_id: str,
        payload: RegisterGroupRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        try:
            result = services.register_participant.execute_group(
                RegisterGroupCommand(
                    event_id=event_id,
                    applicant_name=payload.applicant_name,
                    participants=[
                        GroupParticipantInput(
                            participant_name=item.participant_name,
                            church_or_school=item.church_or_school,
                            grade=item.grade,
                            answers=_normalize_answers(item.answers, item.church_or_school, item.grade),
                        )
                        for item in payload.participants
                    ],
                )
            )
        except EventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RegistrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {
            "registration_id": result.registration.id,
            "count": len(result.participants),
            "participants": [
                {
                    "participant_id": item.participant.id,
                    "name": item.participant.name,
                    "ticket_token": item.ticket.token,
                }
                for item in result.participants
            ],
        }

    @router.post("/api/events/{event_id}/registrations/import-csv")
    async def import_group_csv(
        event_id: str,
        file: UploadFile = File(...),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        raw = await file.read()
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        participants: list[GroupParticipantInput] = []
        applicant_name = "CSV Import"

        for row in reader:
            if not row:
                continue
            participant_name = (row.get("participant_name") or "").strip()
            if not participant_name:
                continue

            row_applicant = (row.get("applicant_name") or "").strip()
            if row_applicant:
                applicant_name = row_applicant

            answers_raw = (row.get("answers_json") or "").strip()
            answers: dict[str, object] = {}
            if answers_raw:
                try:
                    parsed = json.loads(answers_raw)
                    if isinstance(parsed, dict):
                        answers = parsed
                except json.JSONDecodeError:
                    raise HTTPException(status_code=422, detail="invalid answers_json")

            church_or_school = (row.get("church_or_school") or "").strip() or None
            grade = (row.get("grade") or "").strip() or None

            participants.append(
                GroupParticipantInput(
                    participant_name=participant_name,
                    church_or_school=church_or_school,
                    grade=grade,
                    answers=_normalize_answers(answers, church_or_school, grade),
                )
            )

        if not participants:
            raise HTTPException(status_code=422, detail="no participants in csv")

        try:
            result = services.register_participant.execute_group(
                RegisterGroupCommand(
                    event_id=event_id,
                    applicant_name=applicant_name,
                    participants=participants,
                )
            )
        except EventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RegistrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {
            "registration_id": result.registration.id,
            "count": len(result.participants),
        }

    @router.get("/api/events/{event_id}/registrations/export-csv")
    def export_participants_csv(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> Response:
        participants = services.list_participants.execute(ListParticipantsQuery(event_id=event_id))

        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(
            ["participant_id", "name", "church_or_school", "grade", "participant_role", "phone", "registration_fee_paid", "ticket_status"]
        )
        for item in participants:
            writer.writerow(
                [
                    item.participant_id,
                    item.name,
                    item.church_or_school or "",
                    item.grade or "",
                    item.participant_role or "",
                    item.phone or "",
                    item.registration_fee_paid if item.registration_fee_paid is not None else "",
                    item.ticket_status or "",
                ]
            )

        data = stream.getvalue()
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="participants-{event_id}.csv"',
            },
        )

    @router.put("/api/events/{event_id}/meal-slots")
    def configure_meal_slots(
        event_id: str,
        payload: ConfigureMealSlotsRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> list[dict[str, object]]:
        try:
            slots = services.assignment_engine.configure_meal_slots(
                event_id,
                [SlotInput(name=s.name, capacity=s.capacity, sort_order=s.sort_order) for s in payload.slots],
            )
        except AssignmentEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [
            {"id": slot.id, "name": slot.name, "capacity": slot.capacity, "sort_order": slot.sort_order}
            for slot in slots
        ]

    @router.post("/api/events/{event_id}/assignments/meal/run")
    def run_meal_assignment(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, int]:
        try:
            result = services.assignment_engine.run_meal_assignment(event_id)
        except (AssignmentEventNotFoundError, AssignmentCapacityError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"assigned_count": len(result)}

    @router.get("/api/events/{event_id}/assignments/meal")
    def list_meal_assignments(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, str]]:
        result = services.assignment_engine.list_meal_assignments(event_id)
        return [{"participant_id": i.participant_id, "slot_id": i.slot_id} for i in result]

    @router.put("/api/events/{event_id}/groups")
    def configure_groups(
        event_id: str,
        payload: ConfigureGroupsRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> list[dict[str, object]]:
        try:
            groups = services.assignment_engine.configure_groups(
                event_id,
                [SlotInput(name=g.name, capacity=g.capacity, sort_order=g.sort_order) for g in payload.groups],
            )
        except AssignmentEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return [
            {"id": group.id, "name": group.name, "capacity": group.capacity, "sort_order": group.sort_order}
            for group in groups
        ]

    @router.get("/api/events/{event_id}/groups")
    def list_groups(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        groups = services.assignment_engine.list_groups(event_id)
        return [
            {"id": group.id, "name": group.name, "capacity": group.capacity, "sort_order": group.sort_order}
            for group in groups
        ]

    @router.post("/api/events/{event_id}/assignments/group/run")
    def run_group_assignment(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, int]:
        try:
            result = services.assignment_engine.run_group_assignment(event_id)
        except (AssignmentEventNotFoundError, AssignmentCapacityError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"assigned_count": len(result)}

    @router.get("/api/events/{event_id}/assignments/group")
    def list_group_assignments(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, str]]:
        result = services.assignment_engine.list_group_assignments(event_id)
        return [{"participant_id": i.participant_id, "group_id": i.group_id} for i in result]

    @router.get("/api/events/{event_id}/reports/summary")
    def get_report_summary(
        event_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        try:
            summary = services.survey_and_report.get_report_summary(event_id)
        except SurveyEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {
            "registered_count": summary.registered_count,
            "checked_in_count": summary.checked_in_count,
            "survey_response_count": summary.survey_response_count,
            "survey_response_rate": summary.survey_response_rate,
            "survey_average_rating": summary.survey_average_rating,
        }

    @router.post("/api/team/meetings")
    def create_meeting(
        payload: CreateMeetingRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        meeting = services.team_os.create_meeting(
            CreateMeetingCommand(
                org_id=payload.org_id,
                title=payload.title,
                started_at=payload.started_at,
                ended_at=payload.ended_at,
            )
        )
        return {
            "id": meeting.id,
            "org_id": meeting.org_id,
            "title": meeting.title,
            "started_at": meeting.started_at,
            "ended_at": meeting.ended_at,
        }

    @router.get("/api/team/meetings")
    def list_meetings(
        org_id: str = Query(...),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        meetings = services.team_os.list_meetings(org_id)
        return [
            {
                "id": m.id,
                "org_id": m.org_id,
                "title": m.title,
                "started_at": m.started_at,
                "ended_at": m.ended_at,
            }
            for m in meetings
        ]

    @router.post("/api/team/meetings/{meeting_id}/notes")
    def create_meeting_note(
        meeting_id: str,
        payload: CreateMeetingNoteRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        note = services.team_os.add_meeting_note(
            CreateMeetingNoteCommand(
                meeting_id=meeting_id,
                content=payload.content,
            )
        )
        return {
            "id": note.id,
            "meeting_id": note.meeting_id,
            "content": note.content,
            "created_at": note.created_at,
        }

    @router.get("/api/team/meetings/{meeting_id}/notes")
    def list_meeting_notes(
        meeting_id: str,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        notes = services.team_os.list_meeting_notes(meeting_id)
        return [
            {
                "id": note.id,
                "meeting_id": note.meeting_id,
                "content": note.content,
                "created_at": note.created_at,
            }
            for note in notes
        ]

    @router.post("/api/team/action-items")
    def create_action_item(
        payload: CreateActionItemRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        try:
            item = services.team_os.create_action_item(
                CreateActionItemCommand(
                    org_id=payload.org_id,
                    title=payload.title,
                    department=payload.department,
                    due_at=payload.due_at,
                    status=payload.status,
                    event_id=payload.event_id,
                )
            )
        except TeamEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "id": item.id,
            "org_id": item.org_id,
            "title": item.title,
            "department": item.department,
            "due_at": item.due_at,
            "status": item.status,
            "event_id": item.event_id,
        }

    @router.get("/api/team/action-items")
    def list_action_items(
        org_id: str = Query(...),
        status: str | None = Query(default=None),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        items = services.team_os.list_action_items(org_id, status=status)
        return [
            {
                "id": item.id,
                "org_id": item.org_id,
                "title": item.title,
                "department": item.department,
                "due_at": item.due_at,
                "status": item.status,
                "event_id": item.event_id,
            }
            for item in items
        ]

    @router.post("/api/team/documents")
    def create_document(
        payload: CreateTeamDocumentRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, object]:
        try:
            doc = services.team_os.create_document(
                CreateDocumentCommand(
                    org_id=payload.org_id,
                    title=payload.title,
                    kind=payload.kind,
                    content=payload.content,
                    event_id=payload.event_id,
                    version=payload.version,
                )
            )
        except TeamEventNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "id": doc.id,
            "org_id": doc.org_id,
            "title": doc.title,
            "kind": doc.kind,
            "content": doc.content,
            "event_id": doc.event_id,
            "version": doc.version,
        }

    @router.get("/api/team/documents")
    def list_documents(
        org_id: str = Query(...),
        kind: str | None = Query(default=None),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        docs = services.team_os.list_documents(org_id, kind=kind)
        return [
            {
                "id": doc.id,
                "org_id": doc.org_id,
                "title": doc.title,
                "kind": doc.kind,
                "content": doc.content,
                "event_id": doc.event_id,
                "version": doc.version,
            }
            for doc in docs
        ]

    @router.get("/api/public/tickets/{token}")
    def get_public_ticket(token: str) -> dict[str, str]:
        try:
            ticket = services.get_public_ticket.execute(token=token)
        except TicketNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {
            "event_id": ticket.event_id,
            "participant_name": ticket.participant_name,
            "ticket_status": ticket.ticket_status,
        }

    @router.post("/api/checkins")
    def checkin(
        payload: CheckinRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, str]:
        try:
            checkin = services.checkin_by_token.execute(
                CheckinByTokenCommand(
                    event_id=payload.event_id,
                    token=payload.token,
                    checkin_type=payload.checkin_type,
                )
            )
        except InvalidTicketError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DuplicateCheckinError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return {
            "checkin_id": checkin.id,
            "event_id": checkin.event_id,
            "participant_id": checkin.participant_id,
            "type": checkin.type.value,
        }

    @router.post("/api/checkins/by-participant")
    def checkin_by_participant(
        payload: CheckinByParticipantRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, str]:
        try:
            checkin = services.checkin_by_token.execute_for_participant(
                event_id=payload.event_id,
                participant_id=payload.participant_id,
                checkin_type=payload.checkin_type,
            )
        except InvalidTicketError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DuplicateCheckinError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return {
            "checkin_id": checkin.id,
            "event_id": checkin.event_id,
            "participant_id": checkin.participant_id,
            "type": checkin.type.value,
        }

    @router.get("/api/events/{event_id}/participants")
    def list_participants(
        event_id: str,
        church_or_school: str | None = Query(default=None),
        grade: str | None = Query(default=None),
        q: str | None = Query(default=None),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> list[dict[str, object]]:
        participants = services.list_participants.execute(
            ListParticipantsQuery(
                event_id=event_id,
                church_or_school=church_or_school,
                grade=grade,
                q=q,
            )
        )
        return [
            {
                "participant_id": item.participant_id,
                "name": item.name,
                "church_or_school": item.church_or_school,
                "grade": item.grade,
                "participant_role": item.participant_role,
                "phone": item.phone,
                "registration_fee_paid": item.registration_fee_paid,
                "refund_requested": item.refund_requested,
                "refund_status": item.refund_status,
                "refund_reason": item.refund_reason,
                "refund_processed_by": item.refund_processed_by,
                "refund_processed_at": item.refund_processed_at,
                "ticket_status": item.ticket_status,
            }
            for item in participants
        ]

    @router.patch("/api/participants/{participant_id}/answers")
    def update_participant_answers(
        participant_id: str,
        payload: UpdateParticipantAnswersRequest,
        _: str = Depends(require_roles("org_admin", "event_admin", "staff", "leader")),
    ) -> dict[str, object]:
        try:
            participant = services.update_participant_answers.execute(
                UpdateParticipantAnswersCommand(
                    participant_id=participant_id,
                    answers=payload.answers,
                )
            )
        except ParticipantNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {
            "participant_id": participant.id,
            "answers": participant.answers,
        }

    @router.post("/api/participants/{participant_id}/refund-decision")
    def decide_refund(
        participant_id: str,
        payload: RefundDecisionRequest,
        authorization: str | None = Header(default=None, alias="authorization"),
    ) -> dict[str, object]:
        _, approver_name = _require_team_lead_user(authorization)
        try:
            participant = services.update_participant_answers.execute(
                UpdateParticipantAnswersCommand(
                    participant_id=participant_id,
                    answers={
                        "refund_status": "approved" if payload.approve else "rejected",
                        "refund_requested": True,
                        "refund_processed_by": approver_name,
                        "refund_processed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
        except ParticipantNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {
            "participant_id": participant.id,
            "answers": participant.answers,
        }

    @router.get("/api/events/{event_id}/dashboard")
    def get_dashboard(
        event_id: str,
        church_or_school: str | None = Query(default=None),
        grade: str | None = Query(default=None),
        _: str = Depends(require_roles("org_admin", "event_admin", "staff")),
    ) -> dict[str, int]:
        result = services.get_dashboard.execute(
            GetEventDashboardQuery(
                event_id=event_id,
                church_or_school=church_or_school,
                grade=grade,
            )
        )
        return {
            "registered_count": result.registered_count,
            "checked_in_count": result.checked_in_count,
        }

    return router
