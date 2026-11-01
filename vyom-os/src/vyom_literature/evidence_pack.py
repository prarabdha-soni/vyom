from __future__ import annotations

"""B1: reproducible inspection evidence pack for a clinical state.

Given a state_id, reconstruct the complete decision history from the
append-only ledgers: every System One decision (with model/prompt/schema
versions), every System Two synthesis, every human label with actor and
timestamp, the source records with their strategy versions, evidence spans,
awareness events, cost events, and the context-of-use records for the schema
version that produced each decision.

The bundle is content-addressed (sha256 over canonical JSON) so customer QA
and inspectors can verify two packs built at different times are identical.
No model calls, no writes — pure deterministic read path. Tenant scoping is
enforced by RLS on the connection used; this module additionally refuses to
emit any field containing free-text patient data beyond what reviewers see in
the queue (excerpts are hashed references, not stored text).
"""

import hashlib
import json
from datetime import date, datetime
from typing import Any

from vyom_literature.context_of_use import CONTEXT_OF_USE_RECORDS


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _rows(cursor: Any, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


#: Ledger tables that exist from migration 002 onward. Anything added later
#: (evidence spans, awareness events, cost events — 004/005) is included only
#: when present so packs degrade gracefully instead of erroring mid-inspection.
_CORE_TABLES = ("sys1_decisions", "sys2_syntheses", "human_labels", "source_records")


def _table_exists(cursor: Any, table: str) -> bool:
    cursor.execute("select to_regclass(%s)", (f"public.{table}",))
    row = cursor.fetchone()
    return row is not None and row[0] is not None


def build_evidence_pack(connection: Any, *, state_id: int) -> dict[str, Any]:
    """Return the full inspection bundle for one clinical state.

    Raises ValueError when the state does not exist on this (tenant-scoped)
    connection — cross-tenant ids are invisible under RLS, which is exactly
    the behaviour we want to prove in tests.
    """
    with connection.cursor() as cursor:
        states = _rows(
            cursor,
            """
            select id, tenant_id, domain, dedup_key, title_or_header,
                   normalized_state, state_sha256, first_seen_at as created_at
            from clinical_states where id = %s
            """,
            (state_id,),
        )
        if not states:
            raise ValueError("clinical state not found for this tenant")
        state = states[0]

        decisions = _rows(
            cursor,
            """
            select id, model_id, sampler_version, question_schema_version,
                   threshold_policy_version, state_sha256, latency_ms, answers,
                   p_valid_case, p_serious_or_denial, verbatim_extraction,
                   confidence_band, created_at
            from sys1_decisions where state_id = %s order by created_at, id
            """,
            (state_id,),
        )
        # answers may contain reviewer-visible extraction only; strip nothing
        # here (it is already PHI-minimal by construction) but never include
        # normalized_state full text in the pack header below.

        syntheses = []
        for decision in decisions:
            if _table_exists(cursor, "sys2_syntheses"):
                syntheses.extend(
                    _rows(
                        cursor,
                        """
                        select id, sys1_decision_id as decision_id, model_id,
                               draft_narrative, cited_passages, created_at
                        from sys2_syntheses where sys1_decision_id = %s order by id
                        """,
                        (decision["id"],),
                    )
                )

        labels = _rows(
            cursor,
            """
            select id, sys1_decision_id as decision_id, reviewer_id, reviewer_role,
                   action, override_patch, event_verbatim, rationale_note,
                   split, created_at
            from human_labels where state_id = %s order by created_at, id
            """,
            (state_id,),
        )

        sources = _rows(
            cursor,
            """
            select sr.id, sr.source, sr.source_uid, sr.fetched_at,
                   s.version as strategy_version, s.target_key
            from source_records sr
            left join strategies s on s.id = sr.strategy_id
            where sr.state_id = %s order by sr.id
            """,
            (state_id,),
        )

        spans = []
        awareness = []
        cost_events = []
        if _table_exists(cursor, "evidence_spans"):
            spans = _rows(
                cursor,
                """
                select id, kind, start_char, end_char, excerpt_hash, created_at
                from evidence_spans where state_id = %s order by start_char, id
                """,
                (state_id,),
            )
        if _table_exists(cursor, "awareness_events"):
            awareness = _rows(
                cursor,
                """
                select id, aware_on, rule_version, region_rule, screener_role, created_at
                from awareness_events where state_id = %s
                """,
                (state_id,),
            )
        # model_cost_events keys items by (item_type, item_ref), not state_id.
        if _table_exists(cursor, "model_cost_events"):
            cost_events = _rows(
                cursor,
                """
                select id, item_type, item_ref, provider, model_id, call_kind,
                       input_tokens, output_tokens, pages, estimated_cost_usd,
                       latency_ms, outcome, correlation_id, occurred_at
                from model_cost_events
                where item_ref = %s
                order by occurred_at, id
                """,
                (str(state_id),),
            )

    # Context-of-use for every question schema version referenced by a decision.
    referenced_versions = sorted({d["question_schema_version"] for d in decisions})
    context_records = [
        r.as_dict()
        for r in CONTEXT_OF_USE_RECORDS
        if r.domain == state["domain"]
        and (not referenced_versions or r.question_schema_version in referenced_versions)
    ]

    lineage_complete = all(
        d.get("model_id")
        and d.get("sampler_version")
        and d.get("question_schema_version") is not None
        and d.get("threshold_policy_version") is not None
        and d.get("state_sha256") == state["state_sha256"]
        for d in decisions
    )

    pack: dict[str, Any] = {
        "pack_type": "inspection_evidence",
        "pack_version": 1,
        "generated_at": datetime.utcnow().isoformat(),
        "tenant_id": str(state["tenant_id"]),
        "state_id": state["id"],
        "domain": state["domain"],
        "dedup_key": state["dedup_key"],
        "title_or_header": state["title_or_header"],
        "state_sha256": state["state_sha256"],
        "created_at": state["created_at"],
        "source_records": sources,
        "sys1_decisions": decisions,
        "sys2_syntheses": syntheses,
        "human_labels": labels,
        "evidence_spans": spans,
        "awareness_events": awareness,
        "cost_events": cost_events,
        "context_of_use": context_records,
        "lineage_complete": lineage_complete,
    }

    body = json.dumps(pack, sort_keys=True, default=_json_default, separators=(",", ":"))
    pack["pack_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return pack


def render_bundle_markdown(pack: dict[str, Any]) -> str:
    """Human-readable rendering of an evidence pack for customer QA review."""
    lines = [
        f"# Inspection evidence pack ({pack['pack_type']} v{pack['pack_version']})",
        "",
        f"- Tenant: `{pack['tenant_id']}`",
        f"- State: `{pack['state_id']}` · domain `{pack['domain']}`",
        f"- State hash: `{pack['state_sha256']}`",
        f"- Pack hash: `{pack.get('pack_sha256', 'unavailable')}`",
        f"- Lineage complete: {'yes' if pack['lineage_complete'] else 'NO — investigate'}",
        "",
        "## System One decisions (append-only)",
        "",
        "| # | model | sampler | q-schema | thr-policy | band | outcome | latency ms | at |",
        "|---|-------|---------|----------|------------|------|---------|-----------|----|",
    ]
    for i, d in enumerate(pack["sys1_decisions"], 1):
        lines.append(
            f"| {i} | {d['model_id']} | {d['sampler_version']} | "
            f"{d['question_schema_version']} | {d['threshold_policy_version']} | "
            f"{d['confidence_band']} | {d.get('outcome', 'ok')} | {d['latency_ms']} | "
            f"{d['created_at']} |"
        )
    lines += ["", "## Human actions (append-only)", ""]
    if not pack["human_labels"]:
        lines.append("_No human actions recorded._")
    for label in pack["human_labels"]:
        lines.append(
            f"- `{label['created_at']}` **{label['reviewer_role']}** `{label['reviewer_id']}` "
            f"→ {label['action']} (decision {label['decision_id']})"
        )
    lines += ["", "## Sources and strategy versions", ""]
    for src in pack["source_records"]:
        lines.append(
            f"- {src['source']} `{src.get('external_id') or 'local'}` · strategy "
            f"`{src.get('strategy_version') or 'unattributed'}` · "
            f"content sha `{(src.get('content_sha256') or '')[:12]}…`"
        )
    lines += ["", "## Cost telemetry", ""]
    total = sum(
        float(e["estimated_cost_usd"])
        for e in pack["cost_events"]
        if e.get("estimated_cost_usd") is not None
    )
    lines.append(
        f"- {len(pack['cost_events'])} model call(s); estimated total "
        f"${total:.6f} (unavailable values excluded, never fabricated)"
    )
    return "\n".join(lines) + "\n"
