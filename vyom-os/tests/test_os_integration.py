"""End-to-end tests on a real PostgreSQL. Opt-in.

Set ``VYOM_TEST_PG_ADMIN_URL`` to a superuser URL (for example
``postgresql://postgres@127.0.0.1:5432/postgres``). The test creates a
throwaway database, applies migrations 002-009, seeds the fictional
demo-pharma tenant and drops the database afterwards. The ``vyom_app`` and
``vyom_service`` roles must be able to log in (trust auth, or passwords in
``VYOM_TEST_APP_PASSWORD`` / ``VYOM_TEST_SERVICE_PASSWORD``).
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from vyom_os import cases
from vyom_os.ai.gateway import AiGateway
from vyom_os.api import create_app, database_cost_sink
from vyom_os.audit import Actor
from vyom_os.core import Ctx
from vyom_os.db import Database, fetch_value
from vyom_os.security import Authorizer
from vyom_os.seed import seed
from vyom_os.settings import AppSettings
from vyom_os.tenancy import load_tenant_by_slug

ADMIN_URL = os.environ.get("VYOM_TEST_PG_ADMIN_URL", "")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="set VYOM_TEST_PG_ADMIN_URL to run PostgreSQL integration tests")

MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("00[2-9]_*.sql"))
NOW = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
EMAIL_TEXT = (
    "Dear team, I am a general physician in Indore, India. A 39-year-old woman took VY-412 250 mg capsules for "
    "back pain and developed a widespread rash on the third day. She stopped the capsules and recovered. "
    "Please contact me at my clinic for follow-up."
)


def _url(role: str, database: str, password_env: str) -> str:
    params = conninfo_to_dict(ADMIN_URL)
    params.update({"user": role, "dbname": database})
    params.pop("password", None)
    if os.environ.get(password_env):
        params["password"] = os.environ[password_env]
    return make_conninfo(**params)


@pytest.fixture(scope="module")
def env():
    name = f"vyom_it_{secrets.token_hex(4)}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    try:
        with psycopg.connect(make_conninfo(ADMIN_URL, dbname=name), autocommit=True) as connection:
            for migration in MIGRATIONS:
                connection.execute(migration.read_text(encoding="utf-8"))
        password = secrets.token_urlsafe(18)
        settings = AppSettings(
            database_url=_url("vyom_service", name, "VYOM_TEST_SERVICE_PASSWORD"),
            app_database_url=_url("vyom_app", name, "VYOM_TEST_APP_PASSWORD"),
            session_secret=secrets.token_bytes(48),
            ai_mode="demo",
            demo_now=NOW,
        )
        db = Database(settings.database_url, settings.app_database_url)
        gateway = AiGateway(mode="demo", cost_sink=database_cost_sink(db))
        seeded = seed(db, gateway, settings.today(), password)
        from fastapi.testclient import TestClient

        client = TestClient(create_app(settings, database=db, gateway=gateway))
        yield {"db": db, "client": client, "password": password, "seeded": seeded, "gateway": gateway, "settings": settings}
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)')


def _sign_in(env, email):
    response = env["client"].post("/v1/auth/sign-in", json={"email": email, "password": env["password"]})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['token']}", "X-Tenant-ID": body["tenant"]["id"]}


def _other_tenant(env):
    db = env["db"]
    with db.service() as connection:
        connection.execute(
            "insert into tenants (slug, display_name, is_fictional) values ('other-pharma', 'Other Pharma (FICTIONAL)', true) on conflict do nothing"
        )
        connection.execute(
            """
            insert into user_accounts (tenant_id, email, password_hash, role)
            select id, 'reviewer@other-pharma.example', 'scrypt$1$1$1$AA$AA', 'reviewer' from tenants where slug = 'other-pharma'
            on conflict do nothing
            """
        )
        tenant = load_tenant_by_slug(connection, "other-pharma")
        user_id = fetch_value(connection, "select id::text from user_accounts where email = 'reviewer@other-pharma.example'")
        authorizer = Authorizer.load(connection)
    ctx = Ctx(tenant=tenant, actor=Actor(user_id=user_id, role="reviewer", email="reviewer@other-pharma.example"),
              today=env["settings"].today(), authorizer=authorizer, gateway=env["gateway"])
    with db.tenant(tenant.id) as connection:
        if not fetch_value(connection, "select count(*) from products"):
            connection.execute("insert into products (code, name, active_ingredient) values ('VY-412', 'VY-412 (FICTIONAL)', 'sample')")
            cases.intake(connection, ctx, channel="safety_email", source_text=EMAIL_TEXT)
    return tenant


def test_seed_produced_the_sample_tenant(env):
    assert env["seeded"]["status"] == "seeded"
    assert env["seeded"]["report"] == "VY-PBRER-0001"


def test_row_level_security_isolates_tenants(env):
    db = env["db"]
    other = _other_tenant(env)
    demo_id = env["client"].post("/v1/auth/sign-in", json={"email": "reviewer@demo-pharma.example", "password": env["password"]}).json()["tenant"]["id"]
    with db.tenant(demo_id) as connection:
        demo_cases = fetch_value(connection, "select count(*) from cases")
        assert fetch_value(connection, "select count(*) from cases where tenant_id = %s", (other.id,)) == 0
    with db.tenant(other.id) as connection:
        assert fetch_value(connection, "select count(*) from cases") == 1
        assert fetch_value(connection, "select case_number from cases") == "VY-CASE-0001"
    assert demo_cases >= 10
    with psycopg.connect(db.app_url) as connection:
        assert fetch_value(connection, "select count(*) from cases") == 0  # no tenant set: nothing visible
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.tenant(demo_id) as connection:
            connection.execute(
                "insert into products (tenant_id, code, name, active_ingredient) values (%s, 'X-1', 'x', 'x')", (other.id,)
            )


def test_request_role_cannot_read_accounts_or_policies(env):
    db = env["db"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.tenant("00000000-0000-0000-0000-000000000001") as connection:
            connection.execute("select password_hash from user_accounts")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.tenant("00000000-0000-0000-0000-000000000001") as connection:
            connection.execute("update authorization_policies set effect = 'allow'")


def test_decision_records_are_append_only(env):
    db = env["db"]
    with db.service() as connection:
        tenant = load_tenant_by_slug(connection, "demo-pharma")
    # Layer 1: the request role has no UPDATE or DELETE privilege at all.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.tenant(tenant.id) as connection:
            connection.execute("update case_versions set reason = 'changed' where version = 1")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.tenant(tenant.id) as connection:
            connection.execute("delete from audit_events")
    # Layer 2: even the service role, which can UPDATE, is stopped by the trigger.
    for statement in (
        "update case_versions set reason = 'changed' where version = 1",
        "update literature_outcomes set reason = 'changed'",
        "update audit_events set event_type = 'changed'",
    ):
        with pytest.raises(psycopg.errors.RaiseException):
            with db.service() as connection:
                connection.execute(statement)
    # No role used by the application can DELETE at all.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.service() as connection:
            connection.execute("delete from case_versions")


def test_session_and_tenant_header_are_enforced(env):
    client = env["client"]
    reviewer = _sign_in(env, "reviewer@demo-pharma.example")
    assert client.get("/v1/cases").status_code == 401
    assert client.get("/v1/cases", headers={**reviewer, "X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}).status_code == 403
    assert client.get("/v1/cases", headers={"Authorization": "Bearer nonsense", "X-Tenant-ID": reviewer["X-Tenant-ID"]}).status_code == 401
    ops = _sign_in(env, "ops@vyom-internal.example")
    assert client.get("/v1/cases", headers=ops).status_code == 403
    bad = client.post("/v1/auth/sign-in", json={"email": "reviewer@demo-pharma.example", "password": "not-the-password"})
    assert bad.status_code == 401


def test_literature_decision_opens_a_case_and_sweeps_are_idempotent(env):
    client = env["client"]
    reviewer = _sign_in(env, "reviewer@demo-pharma.example")
    queue = client.get("/v1/literature?view=open", headers=reviewer).json()
    assert queue["counts"]["decided"] == 3
    assert queue["items"][0]["band"] == "RED_ESCALATE"
    article = next(item for item in queue["items"] if item["reference"] == "VY-LIT-0011")
    decided = client.post(f"/v1/literature/{article['state_id']}/decision", headers=reviewer,
                          json={"decision_id": article["decision_id"], "outcome": "valid_icsr"})
    assert decided.status_code == 200, decided.text
    case = client.get(f"/v1/cases/{decided.json()['case_number']}", headers=reviewer).json()
    assert case["case"]["source_channel"] == "literature"
    assert case["assessment"]["seriousness"]["criteria"][0] == "death"
    again = client.post(f"/v1/literature/{article['state_id']}/decision", headers=reviewer,
                        json={"decision_id": article["decision_id"], "outcome": "not_relevant"})
    assert again.status_code == 409
    sweep = client.post("/v1/literature/sweeps", headers=reviewer, json={}).json()
    assert sweep["screened"] == 0 and sweep["already_screened"] == 12


def test_case_workflow_roles_and_export(env):
    client = env["client"]
    reviewer = _sign_in(env, "reviewer@demo-pharma.example")
    physician = _sign_in(env, "physician@demo-pharma.example")
    created = client.post("/v1/cases", headers=reviewer, json={"channel": "safety_email", "source_text": EMAIL_TEXT})
    assert created.status_code == 201, created.text
    number = created.json()["case_number"]
    assert client.post("/v1/cases", headers=reviewer, json={"channel": "safety_email", "source_text": EMAIL_TEXT}).status_code == 409

    def view(headers):
        return client.get(f"/v1/cases/{number}", headers=headers).json()

    current = view(reviewer)
    payload = current["payload"]
    payload["reactions"][0]["causality"]["category"] = "probable"
    denied = client.put(f"/v1/cases/{number}", headers=reviewer, json={"expected_version": current["version"]["number"], "payload": payload, "reason": "x"})
    assert denied.status_code == 403
    assert client.post(f"/v1/cases/{number}/narrative", headers=reviewer, json={"expected_version": current["version"]["number"]}).status_code == 200
    current = view(reviewer)
    stale = client.put(f"/v1/cases/{number}", headers=reviewer, json={"expected_version": 1, "payload": current["payload"], "reason": "x"})
    assert stale.status_code == 409
    payload = current["payload"]
    payload["narrative"]["status"] = "edited"
    assert client.put(f"/v1/cases/{number}", headers=reviewer, json={"expected_version": current["version"]["number"], "payload": payload, "reason": "Narrative checked"}).status_code == 200
    current = view(reviewer)
    assert client.post(f"/v1/cases/{number}/transitions", headers=reviewer, json={"action": "submit", "expected_version": current["version"]["number"]}).status_code == 200
    assert client.post(f"/v1/cases/{number}/transitions", headers=reviewer, json={"action": "approve", "expected_version": current["version"]["number"]}).status_code == 403
    early = client.post(f"/v1/cases/{number}/transitions", headers=physician, json={"action": "approve", "expected_version": current["version"]["number"]})
    assert early.status_code == 409 and "causality" in early.json()["detail"]
    current = view(physician)
    payload = current["payload"]
    for reaction in payload["reactions"]:
        reaction["causality"].update({"category": "probable", "comment": "Plausible time to onset; positive dechallenge."})
    assert client.put(f"/v1/cases/{number}", headers=physician, json={"expected_version": current["version"]["number"], "payload": payload, "reason": "Causality"}).status_code == 200
    current = view(physician)
    assert current["payload"]["reactions"][0]["causality"]["assessed_by"] == "physician@demo-pharma.example"
    assert client.post(f"/v1/cases/{number}/transitions", headers=physician, json={"action": "approve", "expected_version": current["version"]["number"]}).status_code == 200
    assert client.post(f"/v1/cases/{number}/exports", headers=reviewer).status_code == 403
    exported = client.post(f"/v1/cases/{number}/exports", headers=physician)
    assert exported.status_code == 201
    download = client.get(f"/v1/cases/{number}/exports/{exported.json()['export_id']}", headers=physician)
    assert download.headers["x-content-sha256"] == exported.json()["sha256"]
    assert "<icsrDraft" in download.text
    history = [event["event_type"] for event in view(physician)["history"]]
    assert {"case_received", "narrative_drafted", "causality_assessed", "case_approve", "e2b_exported"} <= set(history)


def test_report_signoff_needs_complete_sections_and_password(env):
    client = env["client"]
    qppv = _sign_in(env, "qppv@demo-pharma.example")
    physician = _sign_in(env, "physician@demo-pharma.example")
    assert client.post("/v1/reports", headers=physician, json={"product_code": "VY-201", "report_type": "pader", "interval_start": "2026-06-01", "data_lock_point": "2026-11-26"}).status_code == 403
    created = client.post("/v1/reports", headers=qppv, json={"product_code": "VY-201", "report_type": "pader", "interval_start": "2026-06-01", "data_lock_point": "2026-11-26"})
    assert created.status_code == 201, created.text
    number = created.json()["report_number"]
    report = client.get(f"/v1/reports/{number}", headers=qppv).json()
    assert report["content"]["data"]["stats"]["interval_cases"] >= 3
    sign = {"version": report["version"], "meaning": report["signoff_meaning"], "password": env["password"]}
    assert client.post(f"/v1/reports/{number}/signoff", headers=qppv, json=sign).status_code == 409
    assert client.post(f"/v1/reports/{number}/sections/pader_narrative", headers=qppv, json={"expected_version": 1, "action": "accept"}).status_code == 200
    assert client.post(f"/v1/reports/{number}/sections/pader_actions", headers=qppv, json={"expected_version": 2, "action": "edit", "text": "No actions in this interval (SAMPLE DATA)."}).status_code == 200
    sign["version"] = 3
    assert client.post(f"/v1/reports/{number}/signoff", headers=physician, json=sign).status_code == 403
    assert client.post(f"/v1/reports/{number}/signoff", headers=qppv, json={**sign, "password": "not-the-password"}).status_code == 403
    assert client.post(f"/v1/reports/{number}/signoff", headers=qppv, json=sign).status_code == 200
    with pytest.raises(psycopg.errors.RaiseException):
        with env["db"].service() as connection:
            connection.execute("update report_signoffs set meaning = 'changed'")
    assert client.post(f"/v1/reports/{number}/sections/pader_actions", headers=qppv, json={"expected_version": 3, "action": "edit", "text": "late"}).status_code == 409
    assert "Signed off by qppv@demo-pharma.example" in client.get(f"/v1/reports/{number}/export", headers=qppv).text


def test_sign_in_locks_after_repeated_failures(env):
    # Runs last: it locks the admin account for the rest of this module.
    client = env["client"]
    for _ in range(5):
        assert client.post("/v1/auth/sign-in", json={"email": "admin@demo-pharma.example", "password": "not-the-password"}).status_code == 401
    locked = client.post("/v1/auth/sign-in", json={"email": "admin@demo-pharma.example", "password": env["password"]})
    assert locked.status_code == 429
