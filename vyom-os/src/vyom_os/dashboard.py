"""Work overview for the signed-in user's tenant."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from vyom_os import audit, cases, literature, reports
from vyom_os.core import Ctx
from vyom_os.db import fetch_all


def overview(connection: Any, ctx: Ctx) -> dict[str, Any]:
    ctx.require("dashboard.read")
    result: dict[str, Any] = {"today": ctx.today.isoformat(), "tenant": ctx.tenant.public()}

    if ctx.can("literature.read"):
        queue = literature.queue(connection, ctx, view="open", limit=5)
        result["literature"] = {"counts": queue["counts"], "top": queue["items"]}

    if ctx.can("case.read"):
        open_cases = cases.list_cases(connection, ctx, status="open", limit=500)
        items = open_cases["items"]
        by_clock = {"overdue": 0, "due_soon": 0, "on_track": 0}
        for item in items:
            by_clock[item["clock"]["status"]] = by_clock.get(item["clock"]["status"], 0) + 1
        urgent = sorted(items, key=lambda item: item["clock"]["days_remaining"])[:6]
        result["cases"] = {
            "counts": open_cases["counts"],
            "open": len(items),
            "serious_open": sum(1 for item in items if item["serious"]),
            "expedited_candidates": sum(1 for item in items if item["expedited_candidate"]),
            "clock": by_clock,
            "next_due": urgent,
        }

    if ctx.can("report.read"):
        all_reports = reports.list_reports(connection, ctx)
        result["reports"] = {
            "draft": sum(1 for r in all_reports if r["status"] == "draft"),
            "signed_off": sum(1 for r in all_reports if r["status"] == "signed_off"),
            "recent": all_reports[:4],
        }

    week_start = ctx.today - timedelta(days=7)
    result["model_calls"] = fetch_all(
        connection,
        """
        select provider, model_id, call_kind, count(*)::int as calls,
               count(*) filter (where outcome <> 'ok')::int as failed,
               sum(input_tokens)::bigint as input_tokens, sum(output_tokens)::bigint as output_tokens
        from model_cost_events
        where occurred_at >= %s
        group by provider, model_id, call_kind
        order by calls desc
        """,
        (week_start,),
    )
    result["activity"] = audit.recent(connection, limit=12)
    return result
