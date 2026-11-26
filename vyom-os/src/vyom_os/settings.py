"""Runtime configuration for the Vyom OS application.

Secrets come from the environment (a managed secret store in deployment,
``.env.local`` on a laptop). Nothing here has a secret default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from vyom_literature.providers.vertex_ai import VertexSettings

BACKEND_ROOT = Path(__file__).resolve().parents[2]

AiMode = Literal["demo", "live"]


@dataclass(frozen=True)
class LocalModelSettings:
    """OpenAI-compatible endpoint inside the client's network (Ollama, vLLM)."""

    base_url: str
    model_id: str
    api_key: str
    timeout_seconds: int = 60


@dataclass(frozen=True)
class AppSettings:
    database_url: str
    app_database_url: str
    session_secret: bytes
    ai_mode: AiMode
    vertex_fast: VertexSettings | None = None
    vertex_drafting: VertexSettings | None = None
    local_model: LocalModelSettings | None = None
    session_ttl_seconds: int = 8 * 3600
    demo_now: datetime | None = None
    timezone: str = "Asia/Kolkata"
    api_docs: bool = False

    def now(self) -> datetime:
        return self.demo_now or datetime.now(ZoneInfo(self.timezone))

    def today(self) -> date:
        return self.now().astimezone(ZoneInfo(self.timezone)).date()

    @classmethod
    def from_env(cls) -> AppSettings:
        load_dotenv(BACKEND_ROOT / ".env.local", override=False)
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        app_database_url = os.environ.get("APP_DATABASE_URL", "").strip() or database_url

        secret = os.environ.get("VYOM_SESSION_SECRET", "")
        if len(secret) < 32:
            raise ValueError("VYOM_SESSION_SECRET must be at least 32 characters")

        mode = os.environ.get("VYOM_AI_MODE", "demo").strip()
        if mode not in ("demo", "live"):
            raise ValueError("VYOM_AI_MODE must be 'demo' or 'live'")

        vertex_fast = vertex_drafting = None
        if mode == "live":
            vertex_fast = VertexSettings.from_env("VERTEX")
            drafting_model = os.environ.get("VERTEX_DRAFTING_MODEL_ID", "").strip()
            vertex_drafting = replace(
                vertex_fast,
                model_id=drafting_model or vertex_fast.model_id,
                generation=replace(
                    vertex_fast.generation,
                    max_output_tokens=_bounded_int("VERTEX_DRAFTING_MAX_OUTPUT_TOKENS", 8192, 256, 8192),
                    timeout_seconds=_bounded_int("VERTEX_DRAFTING_TIMEOUT_SECONDS", 90, 5, 120),
                ),
            )

        local_model = None
        local_url = os.environ.get("LOCAL_LLM_BASE_URL", "").strip()
        if local_url:
            local_id = os.environ.get("LOCAL_LLM_MODEL", "").strip()
            if not local_id:
                raise ValueError("LOCAL_LLM_MODEL must be pinned when LOCAL_LLM_BASE_URL is set")
            local_model = LocalModelSettings(
                base_url=local_url.rstrip("/"),
                model_id=local_id,
                api_key=os.environ.get("LOCAL_LLM_API_KEY", ""),
                timeout_seconds=_bounded_int("LOCAL_LLM_TIMEOUT_SECONDS", 60, 5, 300),
            )

        demo_now = None
        raw_now = os.environ.get("VYOM_DEMO_NOW", "").strip()
        if raw_now:
            demo_now = datetime.fromisoformat(raw_now)
            if demo_now.tzinfo is None:
                raise ValueError("VYOM_DEMO_NOW must include a UTC offset")

        zone = os.environ.get("VYOM_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"
        try:
            ZoneInfo(zone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("VYOM_TIMEZONE must be an IANA time zone such as Asia/Kolkata") from error

        return cls(
            database_url=database_url,
            app_database_url=app_database_url,
            session_secret=secret.encode("utf-8"),
            ai_mode=mode,  # type: ignore[arg-type]
            vertex_fast=vertex_fast,
            vertex_drafting=vertex_drafting,
            local_model=local_model,
            session_ttl_seconds=_bounded_int("VYOM_SESSION_TTL_SECONDS", 8 * 3600, 300, 24 * 3600),
            demo_now=demo_now,
            timezone=zone,
            api_docs=os.environ.get("VYOM_API_DOCS", "").strip().lower() in {"1", "true", "yes"},
        )


def _bounded_int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, "").strip()
    value = int(raw) if raw else default
    if not low <= value <= high:
        raise ValueError(f"{name} must be within {low}..{high}")
    return value
