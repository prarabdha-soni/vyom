from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    anthropic_api_key: str | None
    ncbi_api_key: str | None
    ncbi_tool: str
    ncbi_email: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(BACKEND_ROOT / ".env.local", override=False)
        return cls(
            database_url=os.environ.get("DATABASE_URL"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            ncbi_api_key=os.environ.get("NCBI_API_KEY"),
            ncbi_tool=os.environ.get("NCBI_TOOL", ""),
            ncbi_email=os.environ.get("NCBI_EMAIL", ""),
        )

    def require_database_url(self) -> str:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        return self.database_url

    def require_anthropic_api_key(self) -> str:
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        return self.anthropic_api_key