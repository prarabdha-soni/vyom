"""Readiness reflects the database, so a load balancer stops routing to a broken replica."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vyom_os.ai.gateway import AiGateway
from vyom_os.api import create_app
from vyom_os.db import Database
from vyom_os.settings import AppSettings

UNREACHABLE = "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1"


def test_health_is_503_while_the_database_is_unreachable():
    settings = AppSettings(database_url=UNREACHABLE, app_database_url=UNREACHABLE, session_secret=b"s" * 48, ai_mode="demo")
    app = create_app(settings, database=Database(UNREACHABLE, UNREACHABLE), gateway=AiGateway(mode="demo"))
    response = TestClient(app).get("/healthz")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
