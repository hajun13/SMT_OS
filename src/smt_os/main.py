from __future__ import annotations

import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from smt_os.application.use_cases.assignment_engine import AssignmentEngineUseCase
from smt_os.application.use_cases.checkin_by_token import CheckinByTokenUseCase
from smt_os.application.use_cases.create_event import CreateEventUseCase
from smt_os.application.use_cases.delete_event import DeleteEventUseCase
from smt_os.application.use_cases.get_event_dashboard import GetEventDashboardUseCase
from smt_os.application.use_cases.get_public_event import GetPublicEventUseCase
from smt_os.application.use_cases.get_public_registration_form import GetPublicRegistrationFormUseCase
from smt_os.application.use_cases.get_public_ticket import GetPublicTicketUseCase
from smt_os.application.use_cases.list_events import ListEventsUseCase
from smt_os.application.use_cases.list_participants import ListParticipantsUseCase
from smt_os.application.use_cases.register_participant import RegisterParticipantUseCase
from smt_os.application.use_cases.survey_and_report import SurveyAndReportUseCase
from smt_os.application.use_cases.team_os import TeamOSUseCase
from smt_os.application.use_cases.update_participant_answers import UpdateParticipantAnswersUseCase
from smt_os.application.use_cases.upsert_registration_form import (
    FieldInput,
    UpsertRegistrationFormCommand,
    UpsertRegistrationFormUseCase,
)
from smt_os.application.ports.repositories import EventRepository, RegistrationFormRepository
from smt_os.config import get_settings, is_placeholder
from smt_os.domain.common.enums import EventTemplate, FieldType
from smt_os.domain.events.entities import Event, EventModules
from smt_os.infrastructure.repositories.in_memory import (
    InMemoryAssignmentRepository,
    InMemoryCheckinRepository,
    InMemoryEventRepository,
    InMemoryParticipantRepository,
    InMemoryRegistrationFormRepository,
    InMemoryRegistrationRepository,
    InMemorySurveyRepository,
    InMemoryTeamRepository,
    InMemoryTicketRepository,
)
from smt_os.interfaces.http.routes import Services, build_router
from smt_os.interfaces.web.router import STATIC_DIR, router as web_router


def _seed_defaults(events: EventRepository, forms: RegistrationFormRepository) -> None:
    default_events = [
        Event(
            id="f8f79bb4-f1c9-48ad-b8ba-8ec15189a2b1",
            org_id="org-1",
            slug="spring-festival-2026",
            title="춘계 페스티벌 2026",
            template=EventTemplate.DAY_EVENT,
            start_at=datetime.fromisoformat("2026-05-16T09:00:00+09:00"),
            end_at=datetime.fromisoformat("2026-05-16T19:00:00+09:00"),
            capacity=300,
            modules=EventModules(seats=False, meals=True, groups=True, activities=True),
        ),
        Event(
            id="7bc5fcb4-bd44-4a28-a8fe-faf159fbd6af",
            org_id="org-1",
            slug="summer-camp-2026",
            title="여름 캠프 2026",
            template=EventTemplate.CAMP,
            start_at=datetime.fromisoformat("2026-08-01T10:00:00+09:00"),
            end_at=datetime.fromisoformat("2026-08-03T16:00:00+09:00"),
            capacity=150,
            modules=EventModules(groups=True, lodging=True, buses=True, meals=True),
        ),
    ]

    form_usecase = UpsertRegistrationFormUseCase(events=events, forms=forms)

    for event in default_events:
        if events.get_by_slug(event.slug) is None:
            events.save(event)

        active = forms.get_active(event.id)
        if active is None:
            form_usecase.execute(
                UpsertRegistrationFormCommand(
                    event_id=event.id,
                    fields=[
                        FieldInput(key="grade", label="학년", type=FieldType.TEXT, required=True, sort_order=1),
                        FieldInput(
                            key="church_or_school",
                            label="교회/학교",
                            type=FieldType.TEXT,
                            required=True,
                            sort_order=2,
                        ),
                        FieldInput(key="allergy", label="알레르기", type=FieldType.TEXTAREA, sort_order=3),
                    ],
                )
            )


def _build_in_memory_services() -> Services:
    events = InMemoryEventRepository()
    registrations = InMemoryRegistrationRepository()
    participants = InMemoryParticipantRepository()
    tickets = InMemoryTicketRepository()
    checkins = InMemoryCheckinRepository()
    forms = InMemoryRegistrationFormRepository()
    assignments = InMemoryAssignmentRepository()
    surveys = InMemorySurveyRepository()
    team = InMemoryTeamRepository()

    _seed_defaults(events, forms)

    return Services(
        create_event=CreateEventUseCase(events),
        delete_event=DeleteEventUseCase(events),
        list_events=ListEventsUseCase(events),
        register_participant=RegisterParticipantUseCase(
            events=events,
            registrations=registrations,
            participants=participants,
            tickets=tickets,
            forms=forms,
        ),
        checkin_by_token=CheckinByTokenUseCase(
            tickets=tickets,
            participants=participants,
            checkins=checkins,
        ),
        get_dashboard=GetEventDashboardUseCase(
            participants=participants,
            checkins=checkins,
        ),
        list_participants=ListParticipantsUseCase(
            participants=participants,
            tickets=tickets,
        ),
        get_public_ticket=GetPublicTicketUseCase(
            tickets=tickets,
            participants=participants,
        ),
        get_public_event=GetPublicEventUseCase(events),
        upsert_registration_form=UpsertRegistrationFormUseCase(
            events=events,
            forms=forms,
        ),
        get_public_registration_form=GetPublicRegistrationFormUseCase(forms=forms),
        assignment_engine=AssignmentEngineUseCase(
            events=events,
            participants=participants,
            assignments=assignments,
        ),
        survey_and_report=SurveyAndReportUseCase(
            events=events,
            participants=participants,
            checkins=checkins,
            surveys=surveys,
        ),
        team_os=TeamOSUseCase(
            events=events,
            team=team,
        ),
        update_participant_answers=UpdateParticipantAnswersUseCase(
            participants=participants,
        ),
    )


def _build_postgres_services(db_url: str) -> Services:
    from smt_os.infrastructure.repositories.postgres import (
        PostgresCheckinRepository,
        PostgresEventRepository,
        PostgresParticipantRepository,
        PostgresRegistrationFormRepository,
        PostgresRegistrationRepository,
        PostgresSessionFactory,
        PostgresTicketRepository,
    )

    session_factory = PostgresSessionFactory(db_url)

    events = PostgresEventRepository(session_factory)
    registrations = PostgresRegistrationRepository(session_factory)
    participants = PostgresParticipantRepository(session_factory)
    tickets = PostgresTicketRepository(session_factory)
    checkins = PostgresCheckinRepository(session_factory)
    forms = PostgresRegistrationFormRepository(session_factory)
    _seed_defaults(events, forms)

    class _NoopAssignmentRepo:
        def replace_meal_slots(self, event_id: str, slots: list[object]) -> None:
            return None

        def list_meal_slots(self, event_id: str) -> list[object]:
            return []

        def replace_meal_assignments(self, event_id: str, items: list[object]) -> None:
            return None

        def list_meal_assignments(self, event_id: str) -> list[object]:
            return []

        def replace_group_slots(self, event_id: str, groups: list[object]) -> None:
            return None

        def list_group_slots(self, event_id: str) -> list[object]:
            return []

        def replace_group_assignments(self, event_id: str, items: list[object]) -> None:
            return None

        def list_group_assignments(self, event_id: str) -> list[object]:
            return []

    class _NoopSurveyRepo:
        def replace_questions(self, event_id: str, questions: list[object]) -> None:
            return None

        def list_questions(self, event_id: str) -> list[object]:
            return []

        def save_response(self, response: object) -> None:
            return None

        def list_responses(self, event_id: str) -> list[object]:
            return []

    assignments = _NoopAssignmentRepo()
    surveys = _NoopSurveyRepo()
    team = InMemoryTeamRepository()

    return Services(
        create_event=CreateEventUseCase(events),
        delete_event=DeleteEventUseCase(events),
        list_events=ListEventsUseCase(events),
        register_participant=RegisterParticipantUseCase(
            events=events,
            registrations=registrations,
            participants=participants,
            tickets=tickets,
            forms=forms,
        ),
        checkin_by_token=CheckinByTokenUseCase(
            tickets=tickets,
            participants=participants,
            checkins=checkins,
        ),
        get_dashboard=GetEventDashboardUseCase(
            participants=participants,
            checkins=checkins,
        ),
        list_participants=ListParticipantsUseCase(
            participants=participants,
            tickets=tickets,
        ),
        get_public_ticket=GetPublicTicketUseCase(
            tickets=tickets,
            participants=participants,
        ),
        get_public_event=GetPublicEventUseCase(events),
        upsert_registration_form=UpsertRegistrationFormUseCase(
            events=events,
            forms=forms,
        ),
        get_public_registration_form=GetPublicRegistrationFormUseCase(forms=forms),
        assignment_engine=AssignmentEngineUseCase(
            events=events,
            participants=participants,
            assignments=assignments,
        ),
        survey_and_report=SurveyAndReportUseCase(
            events=events,
            participants=participants,
            checkins=checkins,
            surveys=surveys,
        ),
        team_os=TeamOSUseCase(
            events=events,
            team=team,
        ),
        update_participant_answers=UpdateParticipantAnswersUseCase(
            participants=participants,
        ),
    )


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.use_postgres:
        missing: list[str] = []
        if is_placeholder(settings.supabase_url):
            missing.append("SUPABASE_URL")
        if is_placeholder(settings.supabase_anon_key):
            missing.append("SUPABASE_ANON_KEY")
        if is_placeholder(settings.supabase_service_role_key):
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if is_placeholder(settings.supabase_db_url):
            missing.append("SUPABASE_DB_URL")
        if missing:
            raise RuntimeError(
                "STORAGE_BACKEND=postgres 설정이지만 Supabase 필수 환경변수가 비어 있거나 샘플값입니다: "
                + ", ".join(missing)
            )
        services = _build_postgres_services(settings.supabase_db_url)
    else:
        services = _build_in_memory_services()

    app = FastAPI(title="S.M.T DooDream OS API", version="0.1.0")
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw_origins:
        allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    else:
        allow_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    allow_origin_regex = os.getenv("CORS_ALLOWED_ORIGIN_REGEX", "").strip() or r"https://.*\.vercel\.app"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
    app.include_router(web_router)
    app.include_router(build_router(services))
    return app


app = create_app()
