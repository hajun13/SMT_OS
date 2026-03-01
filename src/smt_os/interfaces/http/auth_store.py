from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import httpx
from psycopg import connect
from psycopg.rows import dict_row

from smt_os.config import get_settings

AccountType = Literal["ministry", "leader"]
UserStatus = Literal["pending", "approved", "rejected"]


@dataclass(slots=True)
class AuthUser:
    id: str
    email: str
    password_hash: str
    name: str
    account_type: AccountType
    leader_role: str | None
    church_or_school: str | None
    team: str | None
    status: UserStatus
    can_approve: bool
    is_team_lead: bool
    profile_image_url: str | None
    created_at: datetime


_USERS: dict[str, AuthUser] = {}
_EMAIL_INDEX: dict[str, str] = {}
_SESSIONS: dict[str, str] = {}

_BOOTSTRAPPED = False
_SETTINGS = get_settings()
_DB_DSN = _SETTINGS.supabase_db_url if (_SETTINGS.use_postgres and _SETTINGS.supabase_db_url) else None
_SUPABASE_URL = (_SETTINGS.supabase_url or "").rstrip("/")
_SUPABASE_ANON_KEY = _SETTINGS.supabase_anon_key or ""
_SUPABASE_SERVICE_ROLE_KEY = _SETTINGS.supabase_service_role_key or ""


def _superadmin_email() -> str:
    return os.getenv("SUPERADMIN_EMAIL", "superadmin@dodream.local").strip().lower()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db_enabled() -> bool:
    return bool(_DB_DSN)


def _supabase_enabled() -> bool:
    return _db_enabled() and bool(_SUPABASE_URL and _SUPABASE_ANON_KEY)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    if "$" not in password_hash:
        return hmac.compare_digest(password_hash, password)
    salt, expected = password_hash.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(digest, expected)


def _coerce_user(row: dict[str, object]) -> AuthUser:
    return AuthUser(
        id=str(row["id"]),
        email=str(row["email"]),
        password_hash=str(row.get("password_hash") or ""),
        name=str(row["name"]),
        account_type=str(row["account_type"]),  # type: ignore[arg-type]
        leader_role=row.get("leader_role") if isinstance(row.get("leader_role"), str) else None,
        church_or_school=row.get("church_or_school") if isinstance(row.get("church_or_school"), str) else None,
        team=row.get("team") if isinstance(row.get("team"), str) else None,
        status=str(row["status"]),  # type: ignore[arg-type]
        can_approve=bool(row.get("can_approve", False)),
        is_team_lead=bool(row.get("is_team_lead", False)),
        profile_image_url=row.get("profile_image_url") if isinstance(row.get("profile_image_url"), str) else None,
        created_at=row["created_at"],  # type: ignore[assignment]
    )


def _supabase_headers(service: bool = False, token: str | None = None) -> dict[str, str]:
    apikey = _SUPABASE_SERVICE_ROLE_KEY if service else _SUPABASE_ANON_KEY
    headers = {
        "apikey": apikey,
        "content-type": "application/json",
    }
    if token:
        headers["authorization"] = f"Bearer {token}"
    elif service:
        headers["authorization"] = f"Bearer {_SUPABASE_SERVICE_ROLE_KEY}"
    else:
        headers["authorization"] = f"Bearer {_SUPABASE_ANON_KEY}"
    return headers


def _supabase_request(method: str, path: str, *, json: dict[str, object] | None = None, service: bool = False, token: str | None = None) -> dict[str, object]:
    if not _SUPABASE_URL:
        raise ValueError("supabase url is not configured")
    with httpx.Client(timeout=10.0) as client:
        res = client.request(
            method,
            f"{_SUPABASE_URL}{path}",
            headers=_supabase_headers(service=service, token=token),
            json=json,
        )
    if res.status_code >= 400:
        detail: object
        try:
            body = res.json()
            detail = body.get("msg") or body.get("error_description") or body.get("message") or body
        except Exception:
            detail = res.text
        raise ValueError(str(detail))
    return res.json() if res.content else {}


def _bootstrap() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists auth_profiles (
                      user_id uuid primary key,
                      email text not null,
                      name text not null,
                      account_type text not null,
                      leader_role text,
                      church_or_school text,
                      team text,
                      status text not null,
                      can_approve boolean not null default false,
                      is_team_lead boolean not null default false,
                      profile_image_url text,
                      approved_by text,
                      approved_at timestamptz,
                      created_at timestamptz not null default now()
                    )
                    """
                )
                cur.execute(
                    "alter table auth_profiles add column if not exists is_team_lead boolean not null default false"
                )
                cur.execute("alter table auth_profiles add column if not exists profile_image_url text")
            conn.commit()

    ensure_seeded_super_account()
    _BOOTSTRAPPED = True


def _upsert_profile(
    *,
    user_id: str,
    email: str,
    name: str,
    account_type: AccountType,
    leader_role: str | None,
    church_or_school: str | None,
    team: str | None,
    status: UserStatus,
    can_approve: bool,
    is_team_lead: bool = False,
    profile_image_url: str | None = None,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
) -> None:
    if not _db_enabled():
        return
    with connect(_DB_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into auth_profiles (
                  user_id, email, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, approved_by, approved_at, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id) do update set
                  email = excluded.email,
                  name = excluded.name,
                  account_type = excluded.account_type,
                  leader_role = excluded.leader_role,
                  church_or_school = excluded.church_or_school,
                  team = excluded.team,
                  status = excluded.status,
                  can_approve = excluded.can_approve,
                  is_team_lead = excluded.is_team_lead,
                  profile_image_url = excluded.profile_image_url,
                  approved_by = excluded.approved_by,
                  approved_at = excluded.approved_at
                """,
                (
                    user_id,
                    email,
                    name,
                    account_type,
                    leader_role,
                    church_or_school,
                    team,
                    status,
                    can_approve,
                    is_team_lead,
                    profile_image_url,
                    approved_by,
                    approved_at,
                    _now(),
                ),
            )
        conn.commit()


def _profile_by_user_id(user_id: str) -> dict[str, object] | None:
    if not _db_enabled():
        return None
    with connect(_DB_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select user_id, email, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, approved_by, approved_at, created_at
                from auth_profiles
                where user_id = %s
                """,
                (user_id,),
            )
            return cur.fetchone()


def ensure_seeded_super_account() -> None:
    email = _superadmin_email()
    password = os.getenv("SUPERADMIN_PASSWORD", "ChangeMe123!").strip()
    name = os.getenv("SUPERADMIN_NAME", "슈퍼관리자").strip() or "슈퍼관리자"
    team = os.getenv("SUPERADMIN_TEAM", "ops").strip() or "ops"

    if _supabase_enabled() and _SUPABASE_SERVICE_ROLE_KEY:
        user_id: str | None = None
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("select id from auth.users where email = %s", (email,))
                row = cur.fetchone()
                if row is not None:
                    user_id = str(row["id"])
            conn.commit()

        if user_id is None:
            data = _supabase_request(
                "POST",
                "/auth/v1/admin/users",
                service=True,
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"name": name},
                },
            )
            user_id = str((data.get("user") or data).get("id"))
        else:
            # keep seeded super account password in sync with current env
            _supabase_request(
                "PUT",
                f"/auth/v1/admin/users/{user_id}",
                service=True,
                json={
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"name": name},
                },
            )

        _upsert_profile(
            user_id=user_id,
            email=email,
            name=name,
            account_type="ministry",
            leader_role=None,
            church_or_school=None,
            team=team,
            status="approved",
            can_approve=True,
            is_team_lead=True,
            profile_image_url=None,
            approved_by="system",
            approved_at=_now(),
        )
        return

    if email in _EMAIL_INDEX:
        return
    user = AuthUser(
        id=str(uuid4()),
        email=email,
        password_hash=_hash_password(password),
        name=name,
        account_type="ministry",
        leader_role=None,
        church_or_school=None,
        team=team,
        status="approved",
        can_approve=True,
        is_team_lead=True,
        profile_image_url=None,
        created_at=_now(),
    )
    _USERS[user.id] = user
    _EMAIL_INDEX[email] = user.id


def signup(
    *,
    email: str,
    password: str,
    name: str,
    account_type: AccountType,
    leader_role: str | None,
    church_or_school: str | None,
    team: str | None,
) -> AuthUser:
    _bootstrap()
    key = email.strip().lower()
    if not key:
        raise ValueError("email is required")
    if not password.strip():
        raise ValueError("password is required")
    if not name.strip():
        raise ValueError("name is required")

    if account_type == "leader":
        if leader_role not in {"teacher", "evangelist", "pastor"}:
            raise ValueError("leader_role is invalid")
        status: UserStatus = "approved"
        can_approve = False
        is_team_lead = False
        team = None
    else:
        if team not in {"ops", "planning", "education", "life", "promo"}:
            raise ValueError("team is required for ministry")
        status = "pending"
        can_approve = False
        is_team_lead = False
        leader_role = None

    if _supabase_enabled():
        payload = {
            "email": key,
            "password": password,
            "data": {"name": name.strip()},
        }
        data = _supabase_request("POST", "/auth/v1/signup", json=payload)
        user_obj = data.get("user") or {}
        user_id = str(user_obj.get("id"))
        if not user_id or user_id == "None":
            raise ValueError("failed to create auth user")
        _upsert_profile(
            user_id=user_id,
            email=key,
            name=name.strip(),
            account_type=account_type,
            leader_role=leader_role,
            church_or_school=church_or_school.strip() if church_or_school else None,
            team=team,
            status=status,
            can_approve=can_approve,
            is_team_lead=is_team_lead,
            profile_image_url=None,
            approved_by="system" if status == "approved" else None,
            approved_at=_now() if status == "approved" else None,
        )
        return AuthUser(
            id=user_id,
            email=key,
            password_hash="",
            name=name.strip(),
            account_type=account_type,
            leader_role=leader_role,
            church_or_school=church_or_school.strip() if church_or_school else None,
            team=team,
            status=status,
            can_approve=can_approve,
            is_team_lead=is_team_lead,
            profile_image_url=None,
            created_at=_now(),
        )

    if key in _EMAIL_INDEX:
        raise ValueError("email already exists")
    user = AuthUser(
        id=str(uuid4()),
        email=key,
        password_hash=_hash_password(password),
        name=name.strip(),
        account_type=account_type,
        leader_role=leader_role,
        church_or_school=church_or_school.strip() if church_or_school else None,
        team=team,
        status=status,
        can_approve=can_approve,
        is_team_lead=is_team_lead,
        profile_image_url=None,
        created_at=_now(),
    )
    _USERS[user.id] = user
    _EMAIL_INDEX[key] = user.id
    return user


def login(email: str, password: str) -> tuple[str, AuthUser]:
    _bootstrap()
    key = email.strip().lower()

    if _supabase_enabled():
        data = _supabase_request(
            "POST",
            "/auth/v1/token?grant_type=password",
            json={"email": key, "password": password},
        )
        token = str(data.get("access_token") or "")
        user_obj = data.get("user") or {}
        user_id = str(user_obj.get("id") or "")
        if not token or not user_id:
            raise ValueError("invalid credentials")

        profile = _profile_by_user_id(user_id)
        if profile is None:
            # 보호 fallback: 프로필 없으면 leader 최소 권한으로 생성
            _upsert_profile(
                user_id=user_id,
                email=key,
                name=str(user_obj.get("user_metadata", {}).get("name") or user_obj.get("email") or key),
                account_type="leader",
                leader_role="teacher",
                church_or_school=None,
                team=None,
                status="approved",
                can_approve=False,
                is_team_lead=False,
                profile_image_url=None,
                approved_by="system",
                approved_at=_now(),
            )
            profile = _profile_by_user_id(user_id)
        if profile is None:
            raise ValueError("profile not found")
        user = _coerce_user({"id": user_id, **profile, "password_hash": ""})
        return token, user

    user_id = _EMAIL_INDEX.get(key)
    if user_id is None:
        raise ValueError("invalid credentials")
    user = _USERS[user_id]
    if not _verify_password(password, user.password_hash):
        raise ValueError("invalid credentials")
    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = user.id
    return token, user


def get_user_by_token(token: str) -> AuthUser | None:
    _bootstrap()

    if _supabase_enabled():
        try:
            user_obj = _supabase_request("GET", "/auth/v1/user", token=token)
        except ValueError:
            return None
        user_id = str(user_obj.get("id") or "")
        if not user_id:
            return None
        profile = _profile_by_user_id(user_id)
        if profile is None:
            return None
        return _coerce_user({"id": user_id, **profile, "password_hash": ""})

    user_id = _SESSIONS.get(token)
    if user_id is None:
        return None
    return _USERS.get(user_id)


def logout(token: str) -> None:
    _bootstrap()
    if _supabase_enabled():
        # Access token is stateless JWT; client-side token removal is primary.
        return
    _SESSIONS.pop(token, None)


def get_pending_users() -> list[AuthUser]:
    _bootstrap()

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select user_id as id, email, ''::text as password_hash, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, created_at
                    from auth_profiles
                    where account_type = 'ministry' and status = 'pending'
                    order by created_at asc
                    """
                )
                rows = cur.fetchall()
        return [_coerce_user(row) for row in rows]

    return sorted(
        [u for u in _USERS.values() if u.account_type == "ministry" and u.status == "pending"],
        key=lambda u: u.created_at,
    )


def get_ministry_users() -> list[AuthUser]:
    _bootstrap()

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select user_id as id, email, ''::text as password_hash, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, created_at
                    from auth_profiles
                    where account_type = 'ministry'
                    order by created_at asc
                    """
                )
                rows = cur.fetchall()
        return [_coerce_user(row) for row in rows]

    return sorted(
        [u for u in _USERS.values() if u.account_type == "ministry"],
        key=lambda u: u.created_at,
    )


def decide_user(user_id: str, approve: bool) -> AuthUser:
    _bootstrap()

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update auth_profiles
                    set status = %s,
                        approved_at = %s,
                        approved_by = coalesce(approved_by, 'admin')
                    where user_id = %s and account_type = 'ministry'
                    returning user_id as id, email, ''::text as password_hash, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, created_at
                    """,
                    ("approved" if approve else "rejected", _now(), user_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("user not found")
            conn.commit()
        return _coerce_user(row)

    user = _USERS.get(user_id)
    if user is None:
        raise ValueError("user not found")
    if user.account_type != "ministry":
        raise ValueError("only ministry users can be approved")
    user.status = "approved" if approve else "rejected"
    return user


def set_team_lead(user_id: str, is_team_lead: bool) -> AuthUser:
    _bootstrap()

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update auth_profiles
                    set is_team_lead = %s
                    where user_id = %s and account_type = 'ministry' and status = 'approved'
                    returning user_id as id, email, ''::text as password_hash, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, created_at
                    """,
                    (is_team_lead, user_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("approved ministry user not found")
            conn.commit()
        return _coerce_user(row)

    user = _USERS.get(user_id)
    if user is None:
        raise ValueError("user not found")
    if user.account_type != "ministry" or user.status != "approved":
        raise ValueError("approved ministry user not found")
    user.is_team_lead = is_team_lead
    return user


def is_super_admin_user(user: AuthUser) -> bool:
    return user.email.strip().lower() == _superadmin_email()


def set_profile_image(user_id: str, profile_image_url: str | None) -> AuthUser:
    _bootstrap()

    if _db_enabled():
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update auth_profiles
                    set profile_image_url = %s
                    where user_id = %s
                    returning user_id as id, email, ''::text as password_hash, name, account_type, leader_role, church_or_school, team, status, can_approve, is_team_lead, profile_image_url, created_at
                    """,
                    (profile_image_url, user_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("user not found")
            conn.commit()
        return _coerce_user(row)

    user = _USERS.get(user_id)
    if user is None:
        raise ValueError("user not found")
    user.profile_image_url = profile_image_url
    return user


def get_profile_images_by_name(names: list[str]) -> dict[str, str]:
    _bootstrap()
    unique = [name.strip() for name in names if name.strip()]
    if not unique:
        return {}

    if _db_enabled():
        result: dict[str, str] = {}
        with connect(_DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select name, profile_image_url
                    from auth_profiles
                    where profile_image_url is not null
                    """
                )
                rows = cur.fetchall()
        name_set = set(unique)
        for row in rows:
            nm = str(row["name"])
            if nm in name_set:
                img = row.get("profile_image_url")
                if isinstance(img, str) and img:
                    result[nm] = img
        return result

    result: dict[str, str] = {}
    name_set = set(unique)
    for user in _USERS.values():
        if user.name in name_set and user.profile_image_url:
            result[user.name] = user.profile_image_url
    return result


def to_public_user(user: AuthUser) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "account_type": user.account_type,
        "leader_role": user.leader_role,
        "church_or_school": user.church_or_school,
        "team": user.team,
        "status": user.status,
        "can_approve": user.can_approve,
        "is_team_lead": user.is_team_lead,
        "profile_image_url": user.profile_image_url,
        "is_super_admin": is_super_admin_user(user),
    }


def role_for_user(user: AuthUser) -> str:
    if user.account_type == "leader":
        return "leader"
    if user.status == "approved":
        return "event_admin"
    return "pending"
