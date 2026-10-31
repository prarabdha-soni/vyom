from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


DOMAINS = {"pv_literature", "pv_icsr", "hospital_rcm"}
SOURCES = {
    "pubmed",
    "europepmc",
    "hospital_his",
    "partner_e2b",
    "safety_email",
    "call_transcript",
    "hospital_adr_form",
}


class LedgerConflictError(ValueError):
    """Raised when an immutable source identifier is reused for another state."""


@dataclass(frozen=True)
class StateWrite:
    state_id: int
    state_created: bool
    source_created: bool
    state_sha256: str
    normalized_state: dict[str, Any]


def canonical_state_hash(state: dict[str, Any]) -> str:
    encoded = json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def fail_closed_decision(router: Any, state_sha256: str, reason: str) -> dict[str, Any]:
    """Deterministic fallback decision when System One cannot answer.

    A0 non-negotiable: a provider failure must never become GREEN or an
    auto-close. The item is proposed straight to the human review queue with
    full lineage versions so it stays replayable.
    """
    return {
        "model_id": getattr(router, "public_model", "unavailable"),
        "provider": "none",
        "model_version": None,
        "usage": None,
        "sampler_version": router.sampler_version,
        "question_schema_version": router.question_schema_version,
        "threshold_policy_version": router.threshold_policy_version,
        "state_sha256": state_sha256,
        "latency_ms": 0,
        "answers": {},
        "gate_probabilities": {},
        "p_valid_case": None,
        "p_serious_or_denial": None,
        "confidence_band": "YELLOW_REVIEW",
        "recommended_route": None,
        "outcome": "fail_closed",
        "fail_closed_reason": reason[:200],
    }


def record_state_and_source(
    connection: Any,
    *,
    domain: str,
    dedup_key: str,
    title_or_header: str,
    normalized_state: dict[str, Any],
    source: str,
    source_uid: str,
    raw_payload: dict[str, Any] | str,
    strategy_id: int | None = None,
    tenant_id: str | None = None,
) -> StateWrite:
    if domain not in DOMAINS:
        raise ValueError(f"Unsupported domain: {domain}")
    if source not in SOURCES:
        raise ValueError(f"Unsupported source: {source}")
    if not dedup_key or not source_uid or not title_or_header:
        raise ValueError("dedup_key, source_uid, and title_or_header are required")

    state_hash = canonical_state_hash(normalized_state)
    raw_json = raw_payload if isinstance(raw_payload, str) else json.dumps(raw_payload, ensure_ascii=False)
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into clinical_states
                  (domain, dedup_key, title_or_header, normalized_state, state_sha256)
                values (%s, %s, %s, %s::jsonb, %s)
                on conflict (domain, dedup_key) do nothing
                                returning id, state_sha256, normalized_state
                """,
                (
                    domain,
                    dedup_key,
                    title_or_header,
                    json.dumps(normalized_state, ensure_ascii=False),
                    state_hash,
                ),
            )
            state_row = cursor.fetchone()
            state_created = state_row is not None
            if state_row is None:
                cursor.execute(
                    "select id, state_sha256, normalized_state from clinical_states where domain = %s and dedup_key = %s",
                    (domain, dedup_key),
                )
                state_row = cursor.fetchone()
                if state_row is None:
                    raise RuntimeError("Canonical state insert conflicted but no row was found")
            state_id, stored_hash, stored_state = state_row

            cursor.execute(
                """
                insert into source_records (source, source_uid, strategy_id, state_id, raw_payload)
                values (%s, %s, %s, %s, %s::jsonb)
                on conflict (source, source_uid) do nothing
                returning id
                """,
                (source, source_uid, strategy_id, state_id, raw_json),
            )
            source_created = cursor.fetchone() is not None
            if not source_created:
                cursor.execute(
                    "select state_id from source_records where source = %s and source_uid = %s",
                    (source, source_uid),
                )
                source_row = cursor.fetchone()
                if source_row is None:
                    raise RuntimeError("Source insert conflicted but no row was found")
                if source_row[0] != state_id:
                    raise LedgerConflictError("source identifier is already linked to another canonical state")

    return StateWrite(
        state_id=state_id,
        state_created=state_created,
        source_created=source_created,
        state_sha256=str(stored_hash).strip(),
        normalized_state=(
            json.loads(stored_state) if isinstance(stored_state, str) else stored_state
        ),
    )


def append_sys1_decision(connection: Any, *, state_id: int, decision: dict[str, Any]) -> int:
    required = (
        "model_id",
        "sampler_version",
        "question_schema_version",
        "threshold_policy_version",
        "state_sha256",
        "latency_ms",
        "answers",
        "confidence_band",
    )
    missing = [key for key in required if key not in decision]
    if missing:
        raise ValueError(f"Decision is missing required lineage fields: {', '.join(missing)}")

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into sys1_decisions (
                  state_id, model_id, sampler_version, question_schema_version,
                  threshold_policy_version, state_sha256, latency_ms, answers,
                  p_valid_case, p_serious_or_denial, verbatim_extraction, confidence_band
                )
                select id, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                from clinical_states
                where id = %s and state_sha256 = %s
                                on conflict (
                                    state_id, model_id, sampler_version, question_schema_version, threshold_policy_version
                                ) do nothing
                returning id
                """,
                (
                    decision["model_id"],
                    decision["sampler_version"],
                    decision["question_schema_version"],
                    decision["threshold_policy_version"],
                    decision["state_sha256"],
                    decision["latency_ms"],
                    json.dumps(decision["answers"], ensure_ascii=False),
                    decision.get("p_valid_case"),
                    decision.get("p_serious_or_denial"),
                    decision.get("verbatim_extraction"),
                    decision["confidence_band"],
                    state_id,
                    decision["state_sha256"],
                ),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """
                    select id from sys1_decisions
                    where state_id = %s and model_id = %s and sampler_version = %s
                      and question_schema_version = %s and threshold_policy_version = %s
                      and state_sha256 = %s
                    """,
                    (
                        state_id,
                        decision["model_id"],
                        decision["sampler_version"],
                        decision["question_schema_version"],
                        decision["threshold_policy_version"],
                        decision["state_sha256"],
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise LedgerConflictError("decision state hash does not match the immutable clinical state")
            return int(row[0])


def has_sys1_decision(connection: Any, *, state_id: int, decision: dict[str, Any]) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select 1 from sys1_decisions
            where state_id = %s and model_id = %s and sampler_version = %s
              and question_schema_version = %s and threshold_policy_version = %s
              and state_sha256 = %s
            limit 1
            """,
            (
                state_id,
                decision["model_id"],
                decision["sampler_version"],
                decision["question_schema_version"],
                decision["threshold_policy_version"],
                decision["state_sha256"],
            ),
        )
        return cursor.fetchone() is not None


def append_sys2_synthesis(connection: Any, *, decision_id: int, synthesis: Any) -> int:
    draft = synthesis.draft_narrative
    citations = synthesis.cited_passages
    if not isinstance(draft, str) or not draft.strip() or not citations:
        raise ValueError("System Two synthesis requires a draft and cited passages")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into sys2_syntheses (sys1_decision_id, model_id, draft_narrative, cited_passages)
                values (%s, %s, %s, %s::jsonb)
                on conflict (sys1_decision_id) do nothing
                returning id
                """,
                (
                    decision_id,
                    synthesis.model_id,
                    draft,
                    json.dumps(citations, ensure_ascii=False),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "select id from sys2_syntheses where sys1_decision_id = %s",
                    (decision_id,),
                )
                row = cursor.fetchone()
            if row is None:
                raise RuntimeError("System Two synthesis insert returned no id")
            return int(row[0])


def get_sys2_synthesis(connection: Any, *, decision_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select model_id, draft_narrative, cited_passages
            from sys2_syntheses where sys1_decision_id = %s
            """,
            (decision_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {"model_id": row[0], "draft_narrative": row[1], "cited_passages": row[2]}