"""``vyom-weekly-sweep``: the scheduled literature sweep for every client tenant.

Runs as a Kubernetes CronJob. Each tenant is swept in its own RLS-scoped
transaction; a failure is recorded as an ops alert and does not stop the
other tenants. Fictional tenants are skipped unless asked for.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta

from vyom_os import literature
from vyom_os.ai.gateway import AiGateway
from vyom_os.api import database_cost_sink
from vyom_os.audit import Actor
from vyom_os.core import Ctx, DomainError
from vyom_os.db import Database, fetch_all
from vyom_os.security import Authorizer
from vyom_os.settings import AppSettings
from vyom_os.tenancy import load_tenant


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the weekly literature sweep for every client tenant.")
    parser.add_argument("--days", type=int, default=7, help="Window length ending today (default 7).")
    parser.add_argument("--include-fictional", action="store_true", help="Also sweep fictional demo tenants.")
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 92:
        parser.error("--days must be between 1 and 92")

    settings = AppSettings.from_env()
    db = Database(settings.database_url, settings.app_database_url)
    gateway = AiGateway.from_settings(settings, cost_sink=database_cost_sink(db))
    today = settings.today()
    with db.service() as connection:
        tenant_ids = [row["id"] for row in fetch_all(connection, "select id::text as id from tenants where kind <> 'internal' order by slug")]
        authorizer = Authorizer.load(connection)
        tenants = [load_tenant(connection, tenant_id) for tenant_id in tenant_ids]

    failures = 0
    results = []
    for tenant in tenants:
        if tenant is None or tenant.slug == "bootstrap" or (tenant.is_fictional and not args.include_fictional):
            continue
        if gateway.mode == "demo" and not tenant.is_fictional:
            # Not a failure: demo mode never sweeps a real tenant (no live sources, no sample articles).
            results.append({"tenant": tenant.slug, "skipped": "demo mode sweeps only fictional tenants"})
            continue
        ctx = Ctx(tenant=tenant, actor=Actor.system(), today=today, authorizer=authorizer, gateway=gateway)
        try:
            with db.tenant(tenant.id) as connection:
                summary = literature.sweep(connection, ctx, from_date=today - timedelta(days=args.days), to_date=today)
            results.append({"tenant": tenant.slug, **summary})
        except (DomainError, Exception) as error:  # noqa: BLE001 - one tenant must not stop the others
            failures += 1
            message = error.message if isinstance(error, DomainError) else type(error).__name__
            results.append({"tenant": tenant.slug, "error": message})
            with db.service() as connection:
                connection.execute(
                    "insert into ops_alerts (tenant_id, kind, detail) values (%s, 'sweep_failed', %s)",
                    (tenant.id, f"Weekly literature sweep failed: {message}"[:500]),
                )
    json.dump({"date": today.isoformat(), "results": results}, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
