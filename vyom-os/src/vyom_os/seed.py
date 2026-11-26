"""``vyom-seed-demo``: create the fictional demo-pharma tenant with sample work.

Everything created here is SAMPLE DATA: the tenant, its people, products
VY-201 / VY-305 / VY-412, every article and every report. The sample
"history" is produced by running the real services as the fictional users,
so the audit trail looks exactly as it would in use. The deterministic demo
engine is used, never a model.

The password for the sample accounts comes from ``VYOM_DEMO_PASSWORD``; it is
never written to the repository or printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any

from vyom_os import cases, literature, reports
from vyom_os.ai.gateway import AiGateway
from vyom_os.api import database_cost_sink
from vyom_os.audit import Actor
from vyom_os.core import Ctx
from vyom_os.db import Database, Jsonb, fetch_one, fetch_value
from vyom_os.models import CasePayload
from vyom_os.security import MIN_PASSWORD_LENGTH, Authorizer, hash_password
from vyom_os.settings import AppSettings
from vyom_os.tenancy import load_tenant

SLUG = "demo-pharma"
INTERNAL_SLUG = "vyom-internal"
USERS = (
    ("reviewer@demo-pharma.example", "reviewer", SLUG),
    ("physician@demo-pharma.example", "safety_physician", SLUG),
    ("qppv@demo-pharma.example", "qppv", SLUG),
    ("admin@demo-pharma.example", "admin", SLUG),
    ("ops@vyom-internal.example", "ops", INTERNAL_SLUG),
)

# Fictional products with invented reference safety information.
PRODUCTS = (
    {
        "code": "VY-201", "name": "VY-201 (FICTIONAL)", "active_ingredient": "VY-201 active substance (FICTIONAL)",
        "dosage_form": "film-coated tablet", "strength": "25 mg, 50 mg", "ibd": date(2019, 3, 1),
        "terms": ["headache", "dizziness", "cough", "hyperkalaemia", "nausea", "fatigue"],
    },
    {
        "code": "VY-305", "name": "VY-305 (FICTIONAL)", "active_ingredient": "VY-305 active substance (FICTIONAL)",
        "dosage_form": "solution for injection in pre-filled syringe", "strength": "40 mg/0.8 mL", "ibd": date(2021, 8, 16),
        "terms": ["injection site reaction", "upper respiratory tract infection", "pneumonia", "headache", "neutropenia"],
    },
    {
        "code": "VY-412", "name": "VY-412 (FICTIONAL)", "active_ingredient": "VY-412 active substance (FICTIONAL)",
        "dosage_form": "hard capsule", "strength": "250 mg", "ibd": date(2017, 11, 20),
        "terms": ["dizziness", "nausea", "dyspepsia", "rash", "abdominal pain"],
    },
)

NOT_RELEVANT = {
    "VY-LIT-0005": "Animal study; no human subjects.",
    "VY-LIT-0006": "Narrative review; no new patient data.",
    "VY-LIT-0012": "In vitro study; no patients.",
}
# Historical cases taken to approval, with the physician's causality.
APPROVED = {
    "H3": ("probable", "Plausible time to onset; resolved after withdrawal. Underlying kidney disease is a risk factor."),
    "H2": ("probable", "Plausible time to onset; improved after dose reduction."),
    "H1": ("possible", "Plausible time to onset; resolved while treatment continued."),
}


@dataclass
class People:
    reviewer: Ctx
    physician: Ctx
    qppv: Ctx


def _ensure_tenants_and_users(db: Database, password: str) -> dict[str, dict[str, Any]]:
    with db.service() as connection:
        connection.execute(
            """
            insert into tenants (slug, display_name, kind, is_fictional, residency_region, hosted_processing_allowed)
            values (%s, 'Demo Pharma (FICTIONAL)', 'mah', true, 'asia-south1', true)
            on conflict (slug) do nothing
            """,
            (SLUG,),
        )
        connection.execute(
            """
            insert into tenants (slug, display_name, kind, is_fictional, residency_region)
            values (%s, 'Vyom operations', 'internal', false, 'asia-south1')
            on conflict (slug) do nothing
            """,
            (INTERNAL_SLUG,),
        )
        password_hash = hash_password(password)
        accounts = {}
        for email, role, slug in USERS:
            connection.execute(
                """
                insert into user_accounts (tenant_id, email, password_hash, role)
                select id, %s, %s, %s from tenants where slug = %s
                on conflict (email) do nothing
                """,
                (email, password_hash, role, slug),
            )
            accounts[role] = fetch_one(
                connection, "select id::text as id, email, role, tenant_id::text as tenant_id from user_accounts where email = %s", (email,)
            )
        return accounts


def _ctx(db: Database, account: dict[str, Any], gateway: AiGateway, today: date) -> Ctx:
    with db.service() as connection:
        tenant = load_tenant(connection, account["tenant_id"])
        authorizer = Authorizer.load(connection)
    assert tenant is not None
    return Ctx(
        tenant=tenant,
        actor=Actor(user_id=account["id"], role=account["role"], email=account["email"]),
        today=today,
        authorizer=authorizer,
        gateway=gateway,
    )


def _current(db: Database, ctx: Ctx, case_number: str) -> tuple[int, CasePayload]:
    with db.tenant(ctx.tenant.id) as connection:
        view = cases.get_case(connection, ctx, case_number)
    return view["version"]["number"], CasePayload.model_validate(view["payload"])


def _confirm_narrative(db: Database, ctx: Ctx, case_number: str) -> None:
    with db.tenant(ctx.tenant.id) as connection:
        version, _ = _current(db, ctx, case_number)
        cases.draft_narrative(connection, ctx, case_number, expected_version=version)
    version, payload = _current(db, ctx, case_number)
    confirmed = payload.model_copy(update={"narrative": payload.narrative.model_copy(update={"status": "edited"})})
    with db.tenant(ctx.tenant.id) as connection:
        cases.save_version(
            connection, ctx, case_number, expected_version=version, payload=confirmed.model_dump(mode="json"),
            reason="Narrative checked against the source",
        )


def _transition(db: Database, ctx: Ctx, case_number: str, action: str, reason: str | None = None) -> None:
    version, _ = _current(db, ctx, case_number)
    with db.tenant(ctx.tenant.id) as connection:
        cases.transition(connection, ctx, case_number, action=action, expected_version=version, reason=reason)


def seed(db: Database, gateway: AiGateway, today: date, password: str) -> dict[str, Any]:
    accounts = _ensure_tenants_and_users(db, password)
    people = People(
        reviewer=_ctx(db, accounts["reviewer"], gateway, today),
        physician=_ctx(db, accounts["safety_physician"], gateway, today),
        qppv=_ctx(db, accounts["qppv"], gateway, today),
    )
    tenant_id = people.reviewer.tenant.id
    with db.tenant(tenant_id) as connection:
        if fetch_value(connection, "select count(*) from cases") or fetch_value(connection, "select count(*) from products"):
            return {"status": "already seeded", "tenant": SLUG}
        for product in PRODUCTS:
            connection.execute(
                """
                insert into products (code, name, active_ingredient, dosage_form, strength, international_birth_date,
                                      reference_safety_terms, rsi_version)
                values (%s, %s, %s, %s, %s, %s, %s, 'RSI v1 (FICTIONAL)')
                """,
                (
                    product["code"], product["name"], product["active_ingredient"], product["dosage_form"],
                    product["strength"], product["ibd"], Jsonb([{"term": term} for term in product["terms"]]),
                ),
            )

    # Literature: the weekly sweep over the sample articles, then three
    # obvious non-human articles closed by the reviewer.
    with db.tenant(tenant_id) as connection:
        sweep = literature.sweep(connection, people.reviewer)
    with db.tenant(tenant_id) as connection:
        queue = literature.queue(connection, people.reviewer, view="all")["items"]
    for item in queue:
        reason = NOT_RELEVANT.get(item["reference"])
        if reason:
            with db.tenant(tenant_id) as connection:
                literature.decide(
                    connection, people.reviewer, item["state_id"], decision_id=item["decision_id"],
                    outcome="not_relevant", reason=reason,
                )

    # Intake in the order the reports arrived.
    numbers: dict[str, str] = {}
    reports_in = literature.load_fixture("intake.json")["reports"]
    for report in sorted(reports_in, key=lambda r: -int(r["received_days_ago"])):
        with db.tenant(tenant_id) as connection:
            result = cases.intake(
                connection, people.reviewer, channel=report["channel"],
                source_text=literature.fill_dates(report["text"], today), subject=report["subject"],
                received_on=today - timedelta(days=int(report["received_days_ago"])),
            )
        numbers[report["id"]] = result["case_number"]

    # Historical cases: data entry, medical review with causality, approval.
    # The work is done "as of" a few days after each report arrived, so the
    # stored assessments show the clock as it stood then.
    received = {r["id"]: int(r["received_days_ago"]) for r in reports_in}
    for key, (category, comment) in APPROVED.items():
        number = numbers[key]
        worked_on = today - timedelta(days=received[key]) + timedelta(days=6)
        reviewer = replace(people.reviewer, today=worked_on)
        physician = replace(people.physician, today=worked_on)
        _confirm_narrative(db, reviewer, number)
        _transition(db, reviewer, number, "submit")
        version, payload = _current(db, physician, number)
        reactions = [
            r.model_copy(update={"causality": r.causality.model_copy(update={"category": category, "comment": comment})})
            for r in payload.reactions
        ]
        with db.tenant(tenant_id) as connection:
            cases.save_version(
                connection, physician, number, expected_version=version,
                payload=payload.model_copy(update={"reactions": reactions}).model_dump(mode="json"),
                reason="Causality assessment (WHO-UMC)",
            )
        _transition(db, physician, number, "approve")

    # A serious case waiting for the physician, and an invalid report closed.
    _confirm_narrative(db, people.reviewer, numbers["E4"])
    _transition(db, people.reviewer, numbers["E4"], "submit")
    _transition(
        db, people.reviewer, numbers["E7"], "close_invalid",
        reason="No patient and no adverse event. Product quality query passed to the quality team.",
    )

    # A draft PBRER for VY-201 covering the last six months.
    with db.tenant(tenant_id) as connection:
        report = reports.create_report(
            connection, people.qppv, product_code="VY-201", report_type="pbrer",
            interval_start=today - timedelta(days=182), data_lock_point=today,
        )
    return {
        "status": "seeded",
        "tenant": SLUG,
        "users": [email for email, _role, _slug in USERS],
        "literature": {"screened": sweep["screened"], "closed_as_not_relevant": len(NOT_RELEVANT)},
        "cases": numbers,
        "report": report["report_number"],
        "notice": "SAMPLE DATA (FICTIONAL). Sign in with any listed account and VYOM_DEMO_PASSWORD.",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create the fictional demo-pharma tenant with sample work.")
    parser.add_argument(
        "--confirm-fictional", action="store_true",
        help="Confirm that you are loading fictional sample data, never real cases.",
    )
    args = parser.parse_args(argv)
    if not args.confirm_fictional:
        parser.error("pass --confirm-fictional to load the fictional sample tenant")
    password = os.environ.get("VYOM_DEMO_PASSWORD", "")
    if len(password) < MIN_PASSWORD_LENGTH:
        parser.error(f"set VYOM_DEMO_PASSWORD (at least {MIN_PASSWORD_LENGTH} characters) for the sample accounts")
    settings = AppSettings.from_env()
    db = Database(settings.database_url, settings.app_database_url)
    gateway = AiGateway(mode="demo", cost_sink=database_cost_sink(db))
    result = seed(db, gateway, settings.today(), password)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
