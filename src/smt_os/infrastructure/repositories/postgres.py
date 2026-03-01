from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from psycopg import Connection, connect
from psycopg.rows import dict_row

from smt_os.application.ports.repositories import (
    CheckinRepository,
    EventRepository,
    ParticipantRepository,
    RegistrationFormRepository,
    RegistrationRepository,
    TicketRepository,
)
from smt_os.domain.checkins.entities import Checkin
from smt_os.domain.common.enums import CheckinType, EventTemplate, FieldType
from smt_os.domain.events.entities import Event, EventModules
from smt_os.domain.forms.entities import FormField, RegistrationForm
from smt_os.domain.participants.entities import Participant, Registration, Ticket


class PostgresSessionFactory:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def session(self) -> Connection:
        conn = connect(self._dsn, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _event_from_row(row: dict[str, object]) -> Event:
    return Event(
        id=str(row["id"]),
        org_id=str(row["org_id"]),
        slug=str(row["slug"]),
        title=str(row["title"]),
        template=EventTemplate(str(row["template"])),
        start_at=row["start_at"],  # type: ignore[assignment]
        end_at=row["end_at"],  # type: ignore[assignment]
        capacity=int(row["capacity"]),
        modules=EventModules(
            seats=bool(row.get("seats", False)),
            meals=bool(row.get("meals", False)),
            groups=bool(row.get("groups", True)),
            activities=bool(row.get("activities", False)),
            lodging=bool(row.get("lodging", False)),
            buses=bool(row.get("buses", False)),
        ),
    )


class PostgresEventRepository(EventRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, event: Event) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into events (id, org_id, slug, title, template, start_at, end_at, capacity)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id)
                    do update set
                      org_id = excluded.org_id,
                      slug = excluded.slug,
                      title = excluded.title,
                      template = excluded.template,
                      start_at = excluded.start_at,
                      end_at = excluded.end_at,
                      capacity = excluded.capacity
                    """,
                    (
                        event.id,
                        event.org_id,
                        event.slug,
                        event.title,
                        event.template.value,
                        event.start_at,
                        event.end_at,
                        event.capacity,
                    ),
                )
                cur.execute(
                    """
                    insert into event_modules (event_id, seats, meals, groups, activities, lodging, buses)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (event_id)
                    do update set
                      seats = excluded.seats,
                      meals = excluded.meals,
                      groups = excluded.groups,
                      activities = excluded.activities,
                      lodging = excluded.lodging,
                      buses = excluded.buses
                    """,
                    (
                        event.id,
                        event.modules.seats,
                        event.modules.meals,
                        event.modules.groups,
                        event.modules.activities,
                        event.modules.lodging,
                        event.modules.buses,
                    ),
                )

    def get(self, event_id: str) -> Event | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select e.id, e.org_id, e.slug, e.title, e.template, e.start_at, e.end_at, e.capacity,
                           coalesce(m.seats, false) as seats,
                           coalesce(m.meals, false) as meals,
                           coalesce(m.groups, true) as groups,
                           coalesce(m.activities, false) as activities,
                           coalesce(m.lodging, false) as lodging,
                           coalesce(m.buses, false) as buses
                    from events e
                    left join event_modules m on m.event_id = e.id
                    where e.id = %s
                    """,
                    (event_id,),
                )
                row = cur.fetchone()
                return _event_from_row(row) if row else None

    def get_by_slug(self, slug: str) -> Event | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select e.id, e.org_id, e.slug, e.title, e.template, e.start_at, e.end_at, e.capacity,
                           coalesce(m.seats, false) as seats,
                           coalesce(m.meals, false) as meals,
                           coalesce(m.groups, true) as groups,
                           coalesce(m.activities, false) as activities,
                           coalesce(m.lodging, false) as lodging,
                           coalesce(m.buses, false) as buses
                    from events e
                    left join event_modules m on m.event_id = e.id
                    where e.slug = %s
                    order by e.created_at desc
                    limit 1
                    """,
                    (slug,),
                )
                row = cur.fetchone()
                return _event_from_row(row) if row else None

    def list(self) -> list[Event]:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select e.id, e.org_id, e.slug, e.title, e.template, e.start_at, e.end_at, e.capacity,
                           coalesce(m.seats, false) as seats,
                           coalesce(m.meals, false) as meals,
                           coalesce(m.groups, true) as groups,
                           coalesce(m.activities, false) as activities,
                           coalesce(m.lodging, false) as lodging,
                           coalesce(m.buses, false) as buses
                    from events e
                    left join event_modules m on m.event_id = e.id
                    order by e.created_at desc
                    """
                )
                rows = cur.fetchall()
                return [_event_from_row(row) for row in rows]

    def delete(self, event_id: str) -> Event | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from events
                    where id = %s
                    returning id, org_id, slug, title, template, start_at, end_at, capacity
                    """,
                    (event_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Event(
                    id=str(row["id"]),
                    org_id=str(row["org_id"]),
                    slug=str(row["slug"]),
                    title=str(row["title"]),
                    template=EventTemplate(str(row["template"])),
                    start_at=row["start_at"],  # type: ignore[assignment]
                    end_at=row["end_at"],  # type: ignore[assignment]
                    capacity=int(row["capacity"]),
                    modules=EventModules(),
                )


class PostgresRegistrationRepository(RegistrationRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, registration: Registration) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into registrations (id, event_id, kind, applicant_name, created_at)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        registration.id,
                        registration.event_id,
                        registration.kind.value,
                        registration.applicant_name,
                        registration.created_at,
                    ),
                )


class PostgresParticipantRepository(ParticipantRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, participant: Participant) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into participants (
                      id, event_id, registration_id, name, church_or_school, grade, answers, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    on conflict (id) do update set
                      event_id = excluded.event_id,
                      registration_id = excluded.registration_id,
                      name = excluded.name,
                      church_or_school = excluded.church_or_school,
                      grade = excluded.grade,
                      answers = excluded.answers,
                      created_at = excluded.created_at
                    """,
                    (
                        participant.id,
                        participant.event_id,
                        participant.registration_id,
                        participant.name,
                        participant.church_or_school,
                        participant.grade,
                        json.dumps(participant.answers),
                        participant.created_at,
                    ),
                )

    def get(self, participant_id: str) -> Participant | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, event_id, registration_id, name, church_or_school, grade, answers, created_at
                    from participants
                    where id = %s
                    """,
                    (participant_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Participant(
                    id=str(row["id"]),
                    event_id=str(row["event_id"]),
                    registration_id=str(row["registration_id"]),
                    name=str(row["name"]),
                    church_or_school=row.get("church_or_school"),
                    grade=row.get("grade"),
                    answers=row.get("answers") or {},
                    created_at=row["created_at"],  # type: ignore[assignment]
                )

    def list_by_event(
        self,
        event_id: str,
        church_or_school: str | None = None,
        grade: str | None = None,
        name_query: str | None = None,
    ) -> list[Participant]:
        filters = ["event_id = %(event_id)s"]
        params: dict[str, object] = {"event_id": event_id}

        if church_or_school:
            filters.append("church_or_school = %(church_or_school)s")
            params["church_or_school"] = church_or_school
        if grade:
            filters.append("grade = %(grade)s")
            params["grade"] = grade
        if name_query:
            filters.append("name ilike %(name_query)s")
            params["name_query"] = f"%{name_query}%"

        where_clause = " and ".join(filters)

        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    select id, event_id, registration_id, name, church_or_school, grade, answers, created_at
                    from participants
                    where {where_clause}
                    order by created_at desc
                    """,
                    params,
                )
                rows = cur.fetchall()
                return [
                    Participant(
                        id=str(row["id"]),
                        event_id=str(row["event_id"]),
                        registration_id=str(row["registration_id"]),
                        name=str(row["name"]),
                        church_or_school=row.get("church_or_school"),
                        grade=row.get("grade"),
                        answers=row.get("answers") or {},
                        created_at=row["created_at"],  # type: ignore[assignment]
                    )
                    for row in rows
                ]


class PostgresTicketRepository(TicketRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, ticket: Ticket) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into tickets (id, participant_id, token, status, created_at)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (ticket.id, ticket.participant_id, ticket.token, ticket.status, ticket.created_at),
                )

    def find_by_token(self, token: str) -> Ticket | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, participant_id, token, status, created_at
                    from tickets
                    where token = %s
                    """,
                    (token,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Ticket(
                    id=str(row["id"]),
                    participant_id=str(row["participant_id"]),
                    token=str(row["token"]),
                    status=str(row["status"]),
                    created_at=row["created_at"],  # type: ignore[assignment]
                )

    def find_by_participant_id(self, participant_id: str) -> Ticket | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, participant_id, token, status, created_at
                    from tickets
                    where participant_id = %s
                    """,
                    (participant_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return Ticket(
                    id=str(row["id"]),
                    participant_id=str(row["participant_id"]),
                    token=str(row["token"]),
                    status=str(row["status"]),
                    created_at=row["created_at"],  # type: ignore[assignment]
                )


class PostgresCheckinRepository(CheckinRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, checkin: Checkin) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into checkins (id, event_id, participant_id, type, created_at)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (checkin.id, checkin.event_id, checkin.participant_id, checkin.type.value, checkin.created_at),
                )

    def exists(self, event_id: str, participant_id: str, checkin_type: CheckinType) -> bool:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select exists(
                      select 1
                      from checkins
                      where event_id = %s and participant_id = %s and type = %s
                    ) as exists
                    """,
                    (event_id, participant_id, checkin_type.value),
                )
                row = cur.fetchone()
                return bool(row and row["exists"])

    def count_for_participants(
        self,
        event_id: str,
        participant_ids: set[str],
        checkin_type: CheckinType,
    ) -> int:
        if not participant_ids:
            return 0
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select count(*) as cnt
                    from checkins
                    where event_id = %s
                      and type = %s
                      and participant_id = any(%s)
                    """,
                    (event_id, checkin_type.value, list(participant_ids)),
                )
                row = cur.fetchone()
                return int(row["cnt"]) if row else 0


class PostgresRegistrationFormRepository(RegistrationFormRepository):
    def __init__(self, factory: PostgresSessionFactory) -> None:
        self._factory = factory

    def save(self, form: RegistrationForm) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into registration_forms (id, event_id, version, is_active, created_at)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (form.id, form.event_id, form.version, form.is_active, form.created_at),
                )

    def get_active(self, event_id: str) -> RegistrationForm | None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, event_id, version, is_active, created_at
                    from registration_forms
                    where event_id = %s and is_active = true
                    order by version desc
                    limit 1
                    """,
                    (event_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return RegistrationForm(
                    id=str(row["id"]),
                    event_id=str(row["event_id"]),
                    version=int(row["version"]),
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],  # type: ignore[assignment]
                )

    def replace_fields(self, form_id: str, fields: list[FormField]) -> None:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from form_fields where form_id = %s", (form_id,))
                for item in fields:
                    cur.execute(
                        """
                        insert into form_fields (id, form_id, key, label, type, required, options, sort_order)
                        values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (
                            item.id,
                            form_id,
                            item.key,
                            item.label,
                            item.type.value,
                            item.required,
                            json.dumps(item.options),
                            item.sort_order,
                        ),
                    )

    def list_fields(self, form_id: str) -> list[FormField]:
        with self._factory.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, form_id, key, label, type, required, options, sort_order
                    from form_fields
                    where form_id = %s
                    order by sort_order asc
                    """,
                    (form_id,),
                )
                rows = cur.fetchall()
                result: list[FormField] = []
                for row in rows:
                    result.append(
                        FormField(
                            id=str(row["id"]),
                            form_id=str(row["form_id"]),
                            key=str(row["key"]),
                            label=str(row["label"]),
                            type=FieldType(str(row["type"])),
                            required=bool(row["required"]),
                            options=list(row["options"] or []),
                            sort_order=int(row["sort_order"]),
                        )
                    )
                return result


def make_default_form_fields() -> list[FormField]:
    form_id = "default"
    return [
        FormField(
            id=str(uuid4()),
            form_id=form_id,
            key="grade",
            label="학년",
            type=FieldType.TEXT,
            required=True,
            sort_order=1,
        ),
        FormField(
            id=str(uuid4()),
            form_id=form_id,
            key="church_or_school",
            label="교회/학교",
            type=FieldType.TEXT,
            required=True,
            sort_order=2,
        ),
        FormField(
            id=str(uuid4()),
            form_id=form_id,
            key="allergy",
            label="알레르기",
            type=FieldType.TEXTAREA,
            required=False,
            sort_order=3,
        ),
    ]
