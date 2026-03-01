from __future__ import annotations

from collections.abc import Callable

from fastapi import Header, HTTPException

from smt_os.config import get_settings
from smt_os.interfaces.http.auth_store import get_user_by_token, role_for_user

_SETTINGS = get_settings()
_ALLOW_HEADER_ROLE = not _SETTINGS.use_postgres


def _extract_role(x_role: str | None, authorization: str | None) -> str | None:
    if _ALLOW_HEADER_ROLE and x_role:
        return x_role
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix) :].strip()
    if not token:
        return None
    user = get_user_by_token(token)
    if user is None:
        return None
    return role_for_user(user)


def require_roles(*allowed: str) -> Callable[[str | None, str | None], str]:
    def dependency(
        x_role: str | None = Header(default=None, alias="x-role"),
        authorization: str | None = Header(default=None, alias="authorization"),
    ) -> str:
        role = _extract_role(x_role, authorization)
        if role is None:
            raise HTTPException(status_code=401, detail="authentication is required")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="insufficient role")
        return role

    return dependency


def require_team_lead() -> Callable[[str | None], str]:
    def dependency(authorization: str | None = Header(default=None, alias="authorization")) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="authentication is required")
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="authentication is required")
        user = get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid session")
        if user.account_type != "ministry" or user.status != "approved":
            raise HTTPException(status_code=403, detail="insufficient role")
        if not user.is_team_lead:
            raise HTTPException(status_code=403, detail="team lead permission required")
        return user.id

    return dependency
