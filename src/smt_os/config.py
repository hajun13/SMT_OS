from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def read_env_file(filename: str) -> dict[str, str]:
    result: dict[str, str] = {}
    path = Path(filename)
    if not path.exists():
        return result

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


@dataclass(slots=True)
class Settings:
    storage_backend: str
    supabase_url: str | None
    supabase_anon_key: str | None
    supabase_service_role_key: str | None
    supabase_db_url: str | None


    @property
    def use_postgres(self) -> bool:
        return self.storage_backend == "postgres"


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    text = value.strip()
    if not text:
        return True
    lowered = text.lower()
    return "your_project" in lowered or "your_" in lowered


def get_settings() -> Settings:
    merged = read_env_file(".env")
    merged.update(read_env_file(".env.local"))

    for key, value in merged.items():
        if key not in os.environ:
            os.environ[key] = value

    return Settings(
        storage_backend=os.getenv("STORAGE_BACKEND", "in_memory").strip().lower(),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_db_url=os.getenv("SUPABASE_DB_URL"),
    )
