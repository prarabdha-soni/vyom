"""``vyom-admin``: onboard and offboard client tenants, users and products.

For Vyom operators, run inside the deployment (``kubectl exec`` into the API,
or ``docker compose run``). Every change is recorded in the tenant's audit
trail. Passwords are read from a prompt or stdin, never from arguments, and
never printed::

    vyom-admin create-ops-tenant                                    # once per deployment
    vyom-admin add-user vyom-internal you@vyom.example ops
    vyom-admin create-tenant acme-pharma --name "Acme Pharma"
    vyom-admin add-user acme-pharma qppv@acme.example qppv          # prompts for a password
    printf '%s' "$PASSWORD" | vyom-admin add-user acme-pharma r@acme.example reviewer --password-stdin
    vyom-admin add-product acme-pharma product.json
    vyom-admin disable-user r@acme.example
    vyom-admin list

``product.json`` holds ``code``, ``name``, ``active_ingredient`` and the
reference safety information: ``reference_safety_terms`` (a list of terms)
and ``rsi_version``; ``dosage_form``, ``strength`` and
``international_birth_date`` (YYYY-MM-DD) are optional.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from vyom_os import audit
from vyom_os.audit import Actor
from vyom_os.db import Database, Jsonb, fetch_all, fetch_one
from vyom_os.security import MIN_PASSWORD_LENGTH, hash_password

CLIENT_ROLES = ("reviewer", "safety_physician", "qppv", "admin")
INTERNAL_SLUG = "vyom-internal"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OPERATOR = Actor(user_id=None, role="ops", email=None)


class AdminError(Exception):
    """A refused change; nothing was written."""


def database() -> Database:
    service = os.environ.get("DATABASE_URL", "").strip()
    if not service:
        raise AdminError("Set DATABASE_URL (the vyom_service connection).")
    return Database(service, os.environ.get("APP_DATABASE_URL", "").strip() or service)


def _tenant(db: Database, slug: str) -> dict[str, Any]:
    with db.service() as connection:
        row = fetch_one(connection, "select id::text as id, slug, kind, is_fictional from tenants where slug = %s", (slug,))
    if row is None:
        raise AdminError(f"No tenant {slug}.")
    return row


def _record(db: Database, tenant_id: str, kind: str, ref: str, event: str, detail: dict[str, Any]) -> None:
    with db.tenant(tenant_id) as connection:
        audit.record(connection, entity_kind=kind, entity_ref=ref, event_type=event, actor=OPERATOR,
                     detail={**detail, "via": "vyom-admin"})


def create_tenant(db: Database, slug: str, name: str, *, kind: str = "mah", region: str = "asia-south1",
                  hosted_processing: bool = False) -> dict[str, Any]:
    if not SLUG.match(slug) or slug in ("bootstrap", INTERNAL_SLUG):
        raise AdminError("The slug must be 2–63 lowercase letters, digits or hyphens, and not reserved.")
    if kind not in ("mah", "service_provider"):
        raise AdminError("kind must be mah or service_provider.")
    if "(FICTIONAL)" in name.upper():
        raise AdminError("Client tenants are real. The fictional sample comes only from vyom-seed-demo.")
    with db.service() as connection:
        row = fetch_one(
            connection,
            """
            insert into tenants (slug, display_name, kind, is_fictional, residency_region, hosted_processing_allowed)
            values (%s, %s, %s, false, %s, %s)
            on conflict (slug) do nothing
            returning id::text as id, slug
            """,
            (slug, name.strip(), kind, region, hosted_processing),
        )
    if row is None:
        raise AdminError(f"Tenant {slug} already exists.")
    _record(db, row["id"], "tenant", slug, "tenant_created",
            {"name": name.strip(), "kind": kind, "region": region, "hosted_processing": hosted_processing})
    return row


def create_ops_tenant(db: Database, region: str = "asia-south1") -> dict[str, Any]:
    """The operations tenant that holds Vyom's ``ops`` accounts and no safety data. Safe to run again."""
    with db.service() as connection:
        row = fetch_one(
            connection,
            """
            insert into tenants (slug, display_name, kind, is_fictional, residency_region)
            values (%s, 'Vyom operations', 'internal', false, %s)
            on conflict (slug) do nothing
            returning id::text as id, slug
            """,
            (INTERNAL_SLUG, region),
        )
    if row is None:
        return {**_tenant(db, INTERNAL_SLUG), "created": False}
    _record(db, row["id"], "tenant", INTERNAL_SLUG, "tenant_created", {"kind": "internal", "region": region})
    return {**row, "created": True}


def add_user(db: Database, slug: str, email: str, role: str, password: str) -> dict[str, Any]:
    tenant = _tenant(db, slug)
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise AdminError("That is not an email address.")
    allowed = ("ops",) if slug == INTERNAL_SLUG else CLIENT_ROLES
    if role not in allowed:
        raise AdminError(f"Role must be one of: {', '.join(allowed)}.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AdminError(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")
    with db.service() as connection:
        row = fetch_one(
            connection,
            """
            insert into user_accounts (tenant_id, email, password_hash, role)
            values (%s, %s, %s, %s)
            on conflict (email) do nothing
            returning id::text as id, email, role
            """,
            (tenant["id"], email, hash_password(password), role),
        )
    if row is None:
        raise AdminError(f"{email} already has an account.")
    _record(db, tenant["id"], "user", email, "user_added", {"role": role})
    return row


def disable_user(db: Database, email: str) -> dict[str, Any]:
    email = email.strip().lower()
    with db.service() as connection:
        row = fetch_one(
            connection,
            """
            update user_accounts set status = 'disabled' where email = %s and status = 'active'
            returning id::text as id, email, role, tenant_id::text as tenant_id
            """,
            (email,),
        )
    if row is None:
        raise AdminError(f"No active account for {email}.")
    _record(db, row["tenant_id"], "user", email, "user_disabled", {"role": row["role"]})
    return row


def add_product(db: Database, slug: str, product: dict[str, Any]) -> dict[str, Any]:
    tenant = _tenant(db, slug)
    if tenant["kind"] == "internal":
        raise AdminError("The operations tenant has no products.")
    missing = [key for key in ("code", "name", "active_ingredient", "rsi_version") if not str(product.get(key) or "").strip()]
    if missing:
        raise AdminError(f"product.json is missing: {', '.join(missing)}.")
    terms = product.get("reference_safety_terms")
    if not isinstance(terms, list) or not all(isinstance(term, str) and term.strip() for term in terms):
        raise AdminError("reference_safety_terms must be a list of terms from the reference safety information.")
    birth = product.get("international_birth_date")
    if birth is not None:
        try:
            birth = date.fromisoformat(str(birth))
        except ValueError as error:
            raise AdminError("international_birth_date must be YYYY-MM-DD.") from error
    with db.tenant(tenant["id"]) as connection:
        row = fetch_one(
            connection,
            """
            insert into products (code, name, active_ingredient, dosage_form, strength, international_birth_date,
                                  reference_safety_terms, rsi_version)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (tenant_id, code) do nothing
            returning id::text as id, code
            """,
            (
                str(product["code"]).strip(), str(product["name"]).strip(), str(product["active_ingredient"]).strip(),
                product.get("dosage_form"), product.get("strength"), birth,
                Jsonb([{"term": term.strip()} for term in terms]), str(product["rsi_version"]).strip(),
            ),
        )
        if row is None:
            raise AdminError(f"{slug} already has a product {product['code']}.")
        audit.record(connection, entity_kind="product", entity_ref=row["code"], event_type="product_added",
                     actor=OPERATOR, detail={"rsi_version": str(product["rsi_version"]).strip(), "terms": len(terms),
                                             "via": "vyom-admin"})
    return row


def list_tenants(db: Database) -> list[dict[str, Any]]:
    with db.service() as connection:
        return fetch_all(
            connection,
            """
            select t.slug, t.display_name, t.kind, t.is_fictional, t.residency_region,
                   (select count(*) from user_accounts u where u.tenant_id = t.id and u.status = 'active') as active_users,
                   (select count(*) from products p where p.tenant_id = t.id) as products
            from tenants t where t.slug <> 'bootstrap' order by t.slug
            """,
        )


def _password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.read().rstrip("\r\n")
    first = getpass.getpass("Password for the new account: ")
    if getpass.getpass("Repeat it: ") != first:
        raise AdminError("The passwords did not match.")
    return first


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vyom-admin", description="Onboard and offboard client tenants, users and products.")
    commands = parser.add_subparsers(dest="command", required=True)
    ops_tenant = commands.add_parser("create-ops-tenant", help="Create the operations tenant for ops accounts (once).")
    ops_tenant.add_argument("--region", default="asia-south1")
    tenant = commands.add_parser("create-tenant", help="Create a client tenant.")
    tenant.add_argument("slug")
    tenant.add_argument("--name", required=True)
    tenant.add_argument("--kind", default="mah", choices=("mah", "service_provider"))
    tenant.add_argument("--region", default="asia-south1")
    tenant.add_argument("--hosted-processing", action="store_true",
                        help="Allow hosted model processing (needs the client's written approval).")
    user = commands.add_parser("add-user", help="Add a user to a tenant.")
    user.add_argument("slug")
    user.add_argument("email")
    user.add_argument("role", choices=(*CLIENT_ROLES, "ops"))
    user.add_argument("--password-stdin", action="store_true", help="Read the password from stdin instead of a prompt.")
    disable = commands.add_parser("disable-user", help="Disable an account; open sessions stop working within 30 seconds.")
    disable.add_argument("email")
    product = commands.add_parser("add-product", help="Add a product and its reference safety information.")
    product.add_argument("slug")
    product.add_argument("file", type=Path)
    commands.add_parser("list", help="List tenants with active users and products.")
    args = parser.parse_args(argv)

    try:
        db = database()
        if args.command == "create-ops-tenant":
            result: Any = create_ops_tenant(db, args.region)
        elif args.command == "create-tenant":
            result = create_tenant(db, args.slug, args.name, kind=args.kind, region=args.region,
                                        hosted_processing=args.hosted_processing)
        elif args.command == "add-user":
            result = add_user(db, args.slug, args.email, args.role, _password(args.password_stdin))
        elif args.command == "disable-user":
            result = disable_user(db, args.email)
        elif args.command == "add-product":
            result = add_product(db, args.slug, json.loads(args.file.read_text(encoding="utf-8")))
        else:
            result = list_tenants(db)
    except AdminError as error:
        sys.stderr.write(f"vyom-admin: {error}\n")
        sys.exit(2)
    json.dump(result, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
