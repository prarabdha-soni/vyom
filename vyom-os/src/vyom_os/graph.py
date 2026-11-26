"""Provenance-first evidence graph on PostgreSQL (``graph_edges``).

Edges link articles, cases, products and events. Every edge keeps its
provenance and evidence status (verified, reported, inferred, unverified,
ruled_out). The graph never asserts causality; it records what was reported
and what a person confirmed.
"""

from __future__ import annotations

from typing import Any

from vyom_os.db import fetch_all

EVIDENCE_STATUSES = ("verified", "reported", "inferred", "unverified", "ruled_out")


def link(
    connection: Any,
    *,
    from_kind: str,
    from_ref: str,
    relation: str,
    to_kind: str,
    to_ref: str,
    evidence_status: str,
    provenance: str,
    source_state_id: int | None = None,
) -> None:
    if evidence_status not in EVIDENCE_STATUSES:
        raise ValueError("unknown evidence status")
    connection.execute(
        """
        insert into graph_edges
          (from_kind, from_ref, relation, to_kind, to_ref, evidence_status, provenance, source_state_id)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (tenant_id, from_kind, from_ref, relation, to_kind, to_ref, provenance) do nothing
        """,
        (from_kind, from_ref, relation, to_kind, to_ref, evidence_status, provenance, source_state_id),
    )


def set_status(
    connection: Any,
    *,
    from_kind: str,
    from_ref: str,
    relation: str,
    to_kind: str,
    to_ref: str,
    evidence_status: str,
    provenance: str,
) -> bool:
    if evidence_status not in EVIDENCE_STATUSES:
        raise ValueError("unknown evidence status")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update graph_edges set evidence_status = %s, provenance = %s
            where from_kind = %s and from_ref = %s and relation = %s and to_kind = %s and to_ref = %s
            """,
            (evidence_status, provenance, from_kind, from_ref, relation, to_kind, to_ref),
        )
        return cursor.rowcount > 0


def edges_for(connection: Any, *, kind: str, ref: str) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        select from_kind, from_ref, relation, to_kind, to_ref, evidence_status, provenance, created_at
        from graph_edges
        where (from_kind = %s and from_ref = %s) or (to_kind = %s and to_ref = %s)
        order by created_at, id
        """,
        (kind, ref, kind, ref),
    )


def similar_reports(connection: Any, *, product_ref: str, event_refs: list[str], exclude_case: str) -> list[dict[str, Any]]:
    """Other cases with the same suspect product and a shared event term.

    A count of reports, not a signal: signal detection needs exposure data
    and statistical review by a person.
    """
    if not event_refs:
        return []
    return fetch_all(
        connection,
        """
        select event.to_ref as event, count(distinct event.from_ref) as cases,
               array_agg(distinct event.from_ref order by event.from_ref) as case_numbers
        from graph_edges product
        join graph_edges event
          on event.from_kind = 'case' and event.from_ref = product.from_ref
         and event.relation = 'reports_event'
        where product.from_kind = 'case' and product.relation = 'suspect_product'
          and product.evidence_status <> 'ruled_out' and event.evidence_status <> 'ruled_out'
          and product.to_ref = %s and event.to_ref = any(%s) and product.from_ref <> %s
        group by event.to_ref
        order by cases desc, event.to_ref
        """,
        (product_ref, event_refs, exclude_case),
    )
