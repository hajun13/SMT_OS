from __future__ import annotations

import os

os.environ["STORAGE_BACKEND"] = "in_memory"

from fastapi.testclient import TestClient

from smt_os.main import create_app


def _admin_headers() -> dict[str, str]:
    return {"x-role": "event_admin"}


def _staff_headers() -> dict[str, str]:
    return {"x-role": "staff"}


def _create_event(client: TestClient, slug: str = "summer-camp-2026") -> str:
    create_event_res = client.post(
        "/api/events",
        headers=_admin_headers(),
        json={
            "org_id": "org-1",
            "slug": slug,
            "title": "여름 캠프 2026",
            "template": "camp",
            "start_at": "2026-08-01T10:00:00Z",
            "end_at": "2026-08-03T16:00:00Z",
            "capacity": 150,
        },
    )
    assert create_event_res.status_code == 200
    return create_event_res.json()["id"]


def test_web_pages_are_served() -> None:
    client = TestClient(create_app())

    home = client.get("/")
    console = client.get("/console")
    css = client.get("/assets/styles.css")
    landing = client.get("/e/summer-camp-2026")
    register = client.get("/e/summer-camp-2026/register")
    ticket = client.get("/e/summer-camp-2026/ticket")

    assert home.status_code == 200
    assert console.status_code == 200
    assert css.status_code == 200
    assert landing.status_code == 200
    assert register.status_code == 200
    assert ticket.status_code == 200
    assert "gradient" not in css.text


def test_seeded_public_event_and_form() -> None:
    client = TestClient(create_app())

    public_event = client.get("/api/public/events/spring-festival-2026")
    assert public_event.status_code == 200

    event_id = public_event.json()["id"]
    form_res = client.get(f"/api/public/events/{event_id}/registration-form")
    assert form_res.status_code == 200
    keys = [field["key"] for field in form_res.json()]
    assert "grade" in keys
    assert "church_or_school" in keys


def test_registration_validation_with_required_form_fields() -> None:
    client = TestClient(create_app())
    event_id = client.get("/api/public/events/spring-festival-2026").json()["id"]

    invalid_res = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "김운영",
            "participant_name": "박참가",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "11",
            "answers": {},
        },
    )
    assert invalid_res.status_code == 200


def test_group_registration_and_csv_import_export() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="group-event-2026")

    group_res = client.post(
        f"/api/events/{event_id}/registrations/group",
        headers=_staff_headers(),
        json={
            "applicant_name": "단체담당자",
            "participants": [
                {
                    "participant_name": "참가자A",
                    "church_or_school": "서중한합회",
                    "grade": "10",
                    "answers": {},
                },
                {
                    "participant_name": "참가자B",
                    "church_or_school": "서중한합회",
                    "grade": "11",
                    "answers": {},
                },
            ],
        },
    )
    assert group_res.status_code == 200
    assert group_res.json()["count"] == 2

    csv_content = """applicant_name,participant_name,church_or_school,grade\nCSV담당,참가자C,서중한합회,12\nCSV담당,참가자D,서중한합회,9\n"""
    import_res = client.post(
        f"/api/events/{event_id}/registrations/import-csv",
        headers=_staff_headers(),
        files={"file": ("participants.csv", csv_content, "text/csv")},
    )
    assert import_res.status_code == 200
    assert import_res.json()["count"] == 2

    export_res = client.get(
        f"/api/events/{event_id}/registrations/export-csv",
        headers=_staff_headers(),
    )
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "참가자A" in export_res.text
    assert "참가자D" in export_res.text


def test_assignment_engine_meal_and_group() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="assign-event-2026")

    for i in range(1, 7):
        res = client.post(
            "/api/participants/register",
            json={
                "event_id": event_id,
                "applicant_name": f"담당{i}",
                "participant_name": f"참가자{i}",
                "kind": "individual",
                "church_or_school": "서중한합회",
                "grade": str(9 + (i % 3)),
                "answers": {},
            },
        )
        assert res.status_code == 200

    meal_slots = client.put(
        f"/api/events/{event_id}/meal-slots",
        headers=_staff_headers(),
        json={
            "slots": [
                {"name": "A타임", "capacity": 3, "sort_order": 1},
                {"name": "B타임", "capacity": 3, "sort_order": 2},
            ]
        },
    )
    assert meal_slots.status_code == 200
    assert len(meal_slots.json()) == 2

    meal_run = client.post(
        f"/api/events/{event_id}/assignments/meal/run",
        headers=_staff_headers(),
    )
    assert meal_run.status_code == 200
    assert meal_run.json()["assigned_count"] == 6

    meal_result = client.get(
        f"/api/events/{event_id}/assignments/meal",
        headers=_staff_headers(),
    )
    assert meal_result.status_code == 200
    assert len(meal_result.json()) == 6

    groups = client.put(
        f"/api/events/{event_id}/groups",
        headers=_staff_headers(),
        json={
            "groups": [
                {"name": "1조", "capacity": 2, "sort_order": 1},
                {"name": "2조", "capacity": 2, "sort_order": 2},
                {"name": "3조", "capacity": 2, "sort_order": 3},
            ]
        },
    )
    assert groups.status_code == 200
    assert len(groups.json()) == 3

    group_run = client.post(
        f"/api/events/{event_id}/assignments/group/run",
        headers=_staff_headers(),
    )
    assert group_run.status_code == 200
    assert group_run.json()["assigned_count"] == 6

    group_result = client.get(
        f"/api/events/{event_id}/assignments/group",
        headers=_staff_headers(),
    )
    assert group_result.status_code == 200
    assert len(group_result.json()) == 6


def test_survey_and_report_summary() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="report-event-2026")

    for i in range(1, 4):
        reg = client.post(
            "/api/participants/register",
            json={
                "event_id": event_id,
                "applicant_name": f"담당{i}",
                "participant_name": f"리포트참가{i}",
                "kind": "individual",
                "church_or_school": "서중한합회",
                "grade": "11",
                "answers": {},
            },
        )
        token = reg.json()["ticket"]["token"]
        if i <= 2:
            client.post(
                "/api/checkins",
                headers=_staff_headers(),
                json={"event_id": event_id, "token": token, "checkin_type": "entry"},
            )

    upsert_questions = client.put(
        f"/api/events/{event_id}/survey/questions",
        headers=_staff_headers(),
        json={
            "questions": [
                {
                    "key": "overall_rating",
                    "label": "전체 만족도",
                    "type": "rating",
                    "required": True,
                    "sort_order": 1,
                },
                {
                    "key": "comment",
                    "label": "의견",
                    "type": "text",
                    "required": False,
                    "sort_order": 2,
                },
            ]
        },
    )
    assert upsert_questions.status_code == 200

    for rating in [4, 5]:
        submit = client.post(
            f"/api/public/events/{event_id}/survey/responses",
            json={"answers": {"overall_rating": rating, "comment": "좋아요"}},
        )
        assert submit.status_code == 200

    summary = client.get(
        f"/api/events/{event_id}/reports/summary",
        headers=_staff_headers(),
    )
    assert summary.status_code == 200
    assert summary.json() == {
        "registered_count": 3,
        "checked_in_count": 2,
        "survey_response_count": 2,
        "survey_response_rate": 66.67,
        "survey_average_rating": 4.5,
    }


def test_team_os_meeting_action_items_documents() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="team-os-event-2026")

    meeting = client.post(
        "/api/team/meetings",
        headers=_staff_headers(),
        json={
            "org_id": "org-1",
            "title": "운영 주간 회의",
            "started_at": "2026-07-01T10:00:00Z",
        },
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["id"]

    meetings = client.get("/api/team/meetings", headers=_staff_headers(), params={"org_id": "org-1"})
    assert meetings.status_code == 200
    assert any(item["id"] == meeting_id for item in meetings.json())

    meeting_delete = client.delete(f"/api/team/meetings/{meeting_id}", headers=_staff_headers())
    assert meeting_delete.status_code == 200
    meetings_after_delete = client.get("/api/team/meetings", headers=_staff_headers(), params={"org_id": "org-1"})
    assert meetings_after_delete.status_code == 200
    assert all(item["id"] != meeting_id for item in meetings_after_delete.json())

    meeting = client.post(
        "/api/team/meetings",
        headers=_staff_headers(),
        json={
            "org_id": "org-1",
            "title": "운영 주간 회의",
            "started_at": "2026-07-01T10:00:00Z",
        },
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["id"]

    note = client.post(
        f"/api/team/meetings/{meeting_id}/notes",
        headers=_staff_headers(),
        json={"content": "등록률 개선안 논의"},
    )
    assert note.status_code == 200

    notes = client.get(f"/api/team/meetings/{meeting_id}/notes", headers=_staff_headers())
    assert notes.status_code == 200
    assert notes.json()[0]["content"] == "등록률 개선안 논의"

    open_item = client.post(
        "/api/team/action-items",
        headers=_staff_headers(),
        json={
            "org_id": "org-1",
            "title": "청년부 홍보물 배포",
            "department": "홍보",
            "status": "open",
            "event_id": event_id,
        },
    )
    assert open_item.status_code == 200
    open_item_id = open_item.json()["id"]

    done_item = client.post(
        "/api/team/action-items",
        headers=_staff_headers(),
        json={
            "org_id": "org-1",
            "title": "강사 섭외 완료",
            "department": "행정",
            "status": "done",
            "event_id": event_id,
        },
    )
    assert done_item.status_code == 200

    open_items = client.get(
        "/api/team/action-items",
        headers=_staff_headers(),
        params={"org_id": "org-1", "status": "open"},
    )
    assert open_items.status_code == 200
    assert len(open_items.json()) == 1
    assert open_items.json()[0]["status"] == "open"

    action_delete = client.delete(f"/api/team/action-items/{open_item_id}", headers=_staff_headers())
    assert action_delete.status_code == 200
    open_items_after_delete = client.get(
        "/api/team/action-items",
        headers=_staff_headers(),
        params={"org_id": "org-1", "status": "open"},
    )
    assert open_items_after_delete.status_code == 200
    assert len(open_items_after_delete.json()) == 0

    doc = client.post(
        "/api/team/documents",
        headers=_staff_headers(),
        json={
            "org_id": "org-1",
            "title": "캠프 운영 가이드",
            "kind": "guide",
            "content": "체크인 동선과 안전 공지 포함",
            "event_id": event_id,
            "version": 1,
        },
    )
    assert doc.status_code == 200
    doc_id = doc.json()["id"]

    docs = client.get(
        "/api/team/documents",
        headers=_staff_headers(),
        params={"org_id": "org-1", "kind": "guide"},
    )
    assert docs.status_code == 200
    assert len(docs.json()) == 1
    assert docs.json()[0]["title"] == "캠프 운영 가이드"

    doc_delete = client.delete(f"/api/team/documents/{doc_id}", headers=_staff_headers())
    assert doc_delete.status_code == 200
    docs_after_delete = client.get(
        "/api/team/documents",
        headers=_staff_headers(),
        params={"org_id": "org-1", "kind": "guide"},
    )
    assert docs_after_delete.status_code == 200
    assert len(docs_after_delete.json()) == 0


def test_checkin_by_participant_api() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="checkin-by-participant-2026")

    reg = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "담당자",
            "participant_name": "현장참가자",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "11",
            "answers": {},
        },
    )
    assert reg.status_code == 200
    participant_id = reg.json()["participant_id"]

    checkin = client.post(
        "/api/checkins/by-participant",
        headers=_staff_headers(),
        json={
            "event_id": event_id,
            "participant_id": participant_id,
            "checkin_type": "entry",
        },
    )
    assert checkin.status_code == 200
    assert checkin.json()["participant_id"] == participant_id


def test_event_register_checkin_dashboard_flow() -> None:
    client = TestClient(create_app())

    event_id = _create_event(client, slug="camp-autumn-2026")

    register_res = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "김운영",
            "participant_name": "박참가",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "11",
            "answers": {"participant_role": "student"},
        },
    )
    assert register_res.status_code == 200
    token = register_res.json()["ticket"]["token"]

    checkin_res = client.post(
        "/api/checkins",
        headers=_staff_headers(),
        json={
            "event_id": event_id,
            "token": token,
            "checkin_type": "entry",
        },
    )
    assert checkin_res.status_code == 200
    assert checkin_res.json()["type"] == "entry"

    duplicate_checkin_res = client.post(
        "/api/checkins",
        headers=_staff_headers(),
        json={
            "event_id": event_id,
            "token": token,
            "checkin_type": "entry",
        },
    )
    assert duplicate_checkin_res.status_code == 409

    list_events_res = client.get("/api/events", headers=_staff_headers())
    assert list_events_res.status_code == 200
    assert len(list_events_res.json()) >= 3

    participants_res = client.get(
        f"/api/events/{event_id}/participants",
        params={"church_or_school": "서중한합회", "q": "참가"},
        headers=_staff_headers(),
    )
    assert participants_res.status_code == 200
    assert len(participants_res.json()) == 1
    assert participants_res.json()[0]["participant_role"] == "student"
    assert participants_res.json()[0]["phone"] is None
    assert participants_res.json()[0]["registration_fee_paid"] is None

    dashboard_res = client.get(
        f"/api/events/{event_id}/dashboard",
        params={"church_or_school": "서중한합회", "grade": "11"},
        headers=_staff_headers(),
    )
    assert dashboard_res.status_code == 200
    assert dashboard_res.json() == {
        "registered_count": 1,
        "checked_in_count": 1,
    }


def test_teacher_role_requires_phone_and_answers_patch() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="teacher-phone-required-2026")

    invalid = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "인솔자",
            "participant_name": "교사A",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "",
            "answers": {"participant_role": "teacher"},
        },
    )
    assert invalid.status_code == 422

    valid = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "인솔자",
            "participant_name": "교사B",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "",
            "answers": {"participant_role": "teacher", "phone": "010-1111-2222"},
        },
    )
    assert valid.status_code == 200
    participant_id = valid.json()["participant_id"]

    patch = client.patch(
        f"/api/participants/{participant_id}/answers",
        headers=_staff_headers(),
        json={"answers": {"registration_fee_paid": True}},
    )
    assert patch.status_code == 200
    assert patch.json()["answers"]["registration_fee_paid"] is True

    participants = client.get(
        f"/api/events/{event_id}/participants",
        headers=_staff_headers(),
    )
    assert participants.status_code == 200
    assert participants.json()[0]["participant_role"] == "teacher"
    assert participants.json()[0]["phone"] == "010-1111-2222"
    assert participants.json()[0]["registration_fee_paid"] is True


def test_requires_role_header_for_protected_routes() -> None:
    client = TestClient(create_app())

    res = client.get("/api/events")
    assert res.status_code == 401


def test_auth_signup_login_approval_flow() -> None:
    client = TestClient(create_app())

    leader_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "leader@example.com",
            "password": "leader-pass",
            "name": "리더",
            "account_type": "leader",
            "leader_role": "teacher",
            "church_or_school": "서중한합회",
        },
    )
    assert leader_signup.status_code == 200
    assert leader_signup.json()["user"]["status"] == "approved"

    ministry_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "team@example.com",
            "password": "team-pass",
            "name": "팀원",
            "account_type": "ministry",
            "team": "ops",
        },
    )
    assert ministry_signup.status_code == 200
    assert ministry_signup.json()["user"]["status"] == "pending"

    super_login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@dodream.local", "password": "ChangeMe123!"},
    )
    assert super_login.status_code == 200
    super_token = super_login.json()["token"]

    pending = client.get("/api/auth/approvals", headers={"authorization": f"Bearer {super_token}"})
    assert pending.status_code == 200
    assert any(item["email"] == "team@example.com" for item in pending.json())

    team_user_id = next(item["id"] for item in pending.json() if item["email"] == "team@example.com")
    approve = client.post(
        f"/api/auth/approvals/{team_user_id}",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    assert approve.status_code == 200
    assert approve.json()["user"]["status"] == "approved"


def test_event_delete_requires_team_lead() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="delete-target-2026")

    super_login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@dodream.local", "password": "ChangeMe123!"},
    )
    assert super_login.status_code == 200
    super_token = super_login.json()["token"]

    ministry_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "member@example.com",
            "password": "member-pass",
            "name": "팀원",
            "account_type": "ministry",
            "team": "planning",
        },
    )
    assert ministry_signup.status_code == 200

    pending = client.get("/api/auth/approvals", headers={"authorization": f"Bearer {super_token}"})
    member_id = next(item["id"] for item in pending.json() if item["email"] == "member@example.com")
    approve = client.post(
        f"/api/auth/approvals/{member_id}",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    assert approve.status_code == 200

    member_login = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "member-pass"},
    )
    assert member_login.status_code == 200
    member_token = member_login.json()["token"]

    denied = client.delete(f"/api/events/{event_id}", headers={"authorization": f"Bearer {member_token}"})
    assert denied.status_code == 403

    deleted = client.delete(f"/api/events/{event_id}", headers={"authorization": f"Bearer {super_token}"})
    assert deleted.status_code == 200

    events = client.get("/api/events", headers=_admin_headers())
    assert all(item["id"] != event_id for item in events.json())


def test_team_lead_assignment_flow() -> None:
    client = TestClient(create_app())

    super_login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@dodream.local", "password": "ChangeMe123!"},
    )
    assert super_login.status_code == 200
    super_token = super_login.json()["token"]

    ministry_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "leadtarget@example.com",
            "password": "leadtarget-pass",
            "name": "지정대상",
            "account_type": "ministry",
            "team": "education",
        },
    )
    assert ministry_signup.status_code == 200

    pending = client.get("/api/auth/approvals", headers={"authorization": f"Bearer {super_token}"})
    target_id = next(item["id"] for item in pending.json() if item["email"] == "leadtarget@example.com")
    approve = client.post(
        f"/api/auth/approvals/{target_id}",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    assert approve.status_code == 200
    assert approve.json()["user"]["is_team_lead"] is False

    users_before = client.get("/api/auth/ministry-users", headers={"authorization": f"Bearer {super_token}"})
    assert users_before.status_code == 200
    row = next(item for item in users_before.json() if item["id"] == target_id)
    assert row["is_team_lead"] is False

    promote = client.patch(
        f"/api/auth/ministry-users/{target_id}/team-lead",
        headers={"authorization": f"Bearer {super_token}"},
        json={"is_team_lead": True},
    )
    assert promote.status_code == 200
    assert promote.json()["user"]["is_team_lead"] is True

    demote = client.patch(
        f"/api/auth/ministry-users/{target_id}/team-lead",
        headers={"authorization": f"Bearer {super_token}"},
        json={"is_team_lead": False},
    )
    assert demote.status_code == 200
    assert demote.json()["user"]["is_team_lead"] is False


def test_refund_decision_requires_team_lead() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="refund-lead-guard-2026")

    reg = client.post(
        "/api/participants/register",
        json={
            "event_id": event_id,
            "applicant_name": "담당자",
            "participant_name": "환불대상",
            "kind": "individual",
            "church_or_school": "서중한합회",
            "grade": "11",
            "answers": {"participant_role": "student", "refund_requested": True, "refund_status": "pending"},
        },
    )
    participant_id = reg.json()["participant_id"]

    super_login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@dodream.local", "password": "ChangeMe123!"},
    )
    super_token = super_login.json()["token"]

    ministry_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "refund-member@example.com",
            "password": "refund-pass",
            "name": "일반팀원",
            "account_type": "ministry",
            "team": "ops",
        },
    )
    assert ministry_signup.status_code == 200
    pending = client.get("/api/auth/approvals", headers={"authorization": f"Bearer {super_token}"})
    user_id = next(item["id"] for item in pending.json() if item["email"] == "refund-member@example.com")
    client.post(
        f"/api/auth/approvals/{user_id}",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    member_login = client.post(
        "/api/auth/login",
        json={"email": "refund-member@example.com", "password": "refund-pass"},
    )
    member_token = member_login.json()["token"]

    denied = client.post(
        f"/api/participants/{participant_id}/refund-decision",
        headers={"authorization": f"Bearer {member_token}"},
        json={"approve": True},
    )
    assert denied.status_code == 403

    approved = client.post(
        f"/api/participants/{participant_id}/refund-decision",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    assert approved.status_code == 200
    assert approved.json()["answers"]["refund_status"] == "approved"


def test_public_participant_info() -> None:
    client = TestClient(create_app())
    event_id = _create_event(client, slug="public-info-2026")

    save = client.post(
        "/api/team/documents",
        headers=_admin_headers(),
        json={
            "org_id": "org-1",
            "title": "참가자 필독",
            "kind": "participant_info",
            "content": "등록비, 준비물, 집결 시간을 확인하세요.",
            "event_id": event_id,
            "version": 1,
        },
    )
    assert save.status_code == 200

    info = client.get(f"/api/public/events/{event_id}/participant-info")
    assert info.status_code == 200
    assert info.json()["title"] == "참가자 필독"
    assert "등록비" in info.json()["content"]

    # 같은 이벤트 participant_info는 덮어쓰기(1건 유지)되어야 한다.
    update = client.post(
        "/api/team/documents",
        headers=_admin_headers(),
        json={
            "org_id": "org-1",
            "title": "참가자 최종 안내",
            "kind": "participant_info",
            "content": "최종 집결 시간은 오전 9시입니다.",
            "event_id": event_id,
            "version": 1,
        },
    )
    assert update.status_code == 200
    assert update.json()["version"] == 2

    docs = client.get(
        f"/api/team/documents?org_id=org-1&kind=participant_info",
        headers=_admin_headers(),
    )
    assert docs.status_code == 200
    same_event_docs = [item for item in docs.json() if item["event_id"] == event_id]
    assert len(same_event_docs) == 1
    assert same_event_docs[0]["title"] == "참가자 최종 안내"


def test_profile_image_and_public_org_chart() -> None:
    client = TestClient(create_app())

    super_login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@dodream.local", "password": "ChangeMe123!"},
    )
    assert super_login.status_code == 200
    super_token = super_login.json()["token"]

    signup = client.post(
        "/api/auth/signup",
        json={
            "email": "orgchart-ops@example.com",
            "password": "orgchart-pass",
            "name": "정하준",
            "account_type": "ministry",
            "team": "ops",
        },
    )
    assert signup.status_code == 200

    pending = client.get("/api/auth/approvals", headers={"authorization": f"Bearer {super_token}"})
    target_id = next(item["id"] for item in pending.json() if item["email"] == "orgchart-ops@example.com")
    approve = client.post(
        f"/api/auth/approvals/{target_id}",
        headers={"authorization": f"Bearer {super_token}"},
        json={"approve": True},
    )
    assert approve.status_code == 200

    member_login = client.post(
        "/api/auth/login",
        json={"email": "orgchart-ops@example.com", "password": "orgchart-pass"},
    )
    assert member_login.status_code == 200
    token = member_login.json()["token"]

    image_res = client.patch(
        "/api/auth/me/profile-image",
        headers={"authorization": f"Bearer {token}"},
        json={"image_data_url": "data:image/png;base64,AAA"},
    )
    assert image_res.status_code == 200
    assert image_res.json()["user"]["profile_image_url"] == "data:image/png;base64,AAA"

    chart = client.get("/api/public/org-chart")
    assert chart.status_code == 200
    flat = [m for t in chart.json() for m in t["members"]]
    me = next((m for m in flat if m["name"] == "정하준"), None)
    assert me is not None
    assert me["photo_url"] == "data:image/png;base64,AAA"
