from __future__ import annotations

import math
from typing import Any, Literal
from uuid import UUID


ReviewRole = Literal["safety_physician", "pv_associate", "cpc_coder", "tpa_auditor"]
ReviewAction = Literal["ACCEPT", "CORRECT", "ESCALATE"]
VALID_ROLES = {"safety_physician", "pv_associate", "cpc_coder", "tpa_auditor"}
VALID_ACTIONS = {"ACCEPT", "CORRECT", "ESCALATE"}


def fetch_review_queue(
    connection: Any, *, domain: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    if domain is not None and domain not in {"pv_literature", "pv_icsr"}:
        raise ValueError("unsupported review domain")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")

    params: list[Any] = []
    domain_filter = ""
    if domain:
        domain_filter = "and cs.domain = %s"
        params.append(domain)
    params.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            with latest_decision as (
              select distinct on (d.state_id)
                d.id, d.state_id, d.model_id, d.sampler_version,
                d.question_schema_version, d.threshold_policy_version,
                d.answers, d.confidence_band, d.created_at
              from sys1_decisions d
              order by d.state_id, d.created_at desc, d.id desc
            )
            select cs.id, cs.domain, cs.title_or_header, cs.normalized_state,
              ld.id, ld.model_id, ld.sampler_version, ld.question_schema_version,
              ld.threshold_policy_version, ld.answers, ld.confidence_band,
              latest_label.action, latest_label.rationale_note
            from latest_decision ld
            join clinical_states cs on cs.id = ld.state_id
            left join lateral (
              select label.action, label.rationale_note
              from human_labels label
              where label.sys1_decision_id = ld.id
              order by label.created_at desc, label.id desc
              limit 1
            ) latest_label on true
            where (
              ld.confidence_band in ('YELLOW_REVIEW', 'RED_ESCALATE')
              or latest_label.action = 'ESCALATE'
            )
            and (latest_label.action is null or latest_label.action = 'ESCALATE')
            {domain_filter}
            order by
              (latest_label.action = 'ESCALATE') desc nulls last,
              (ld.confidence_band = 'RED_ESCALATE') desc,
              coalesce((ld.answers->'is_serious_event'->>'probability')::numeric, 0) desc,
              cs.first_seen_at asc
            limit %s
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
    return [
        {
            "state_id": row[0],
            "domain": row[1],
            "title_or_header": row[2],
            "normalized_state": row[3],
            "decision_id": row[4],
            "model_id": row[5],
            "sampler_version": row[6],
            "question_schema_version": row[7],
            "threshold_policy_version": row[8],
            "answers": row[9],
            "confidence_band": row[10],
            "latest_action": row[11],
            "latest_rationale": row[12],
        }
        for row in rows
    ]


def append_review_label(
    connection: Any,
    *,
    state_id: int,
    decision_id: int,
    reviewer_id: UUID,
    reviewer_role: ReviewRole,
    action: ReviewAction,
    override_patch: dict[str, Any] | None = None,
    event_verbatim: str | None = None,
    rationale_note: str | None = None,
) -> int:
    if reviewer_role not in VALID_ROLES or action not in VALID_ACTIONS:
        raise ValueError("invalid reviewer role or action")
    if action == "CORRECT" and not override_patch:
        raise ValueError("CORRECT requires a non-empty override_patch")
    if action == "ESCALATE" and override_patch:
        raise ValueError("ESCALATE cannot assert a ground-truth override")
    if event_verbatim is not None and len(event_verbatim) > 2000:
        raise ValueError("event_verbatim exceeds the maximum length")

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                "select 1 from sys1_decisions where id = %s and state_id = %s",
                (decision_id, state_id),
            )
            if cursor.fetchone() is None:
                raise ValueError("decision does not belong to the requested state")
            cursor.execute(
                """
                insert into human_labels (
                  state_id, sys1_decision_id, reviewer_id, reviewer_role,
                  action, override_patch, event_verbatim, rationale_note, split
                ) values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, 'pool')
                returning id
                """,
                (
                    state_id,
                    decision_id,
                    str(reviewer_id),
                    reviewer_role,
                    action,
                    json_dumps(override_patch),
                    event_verbatim,
                    rationale_note,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("review label insert returned no id")
            return int(row[0])


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def wilson_interval(successes: int, trials: int, z_score: float = 1.959963984540054) -> tuple[float, float] | None:
    if trials <= 0:
        return None
    proportion = successes / trials
    denominator = 1 + z_score**2 / trials
    center = (proportion + z_score**2 / (2 * trials)) / denominator
    margin = (
        z_score
        * math.sqrt(proportion * (1 - proportion) / trials + z_score**2 / (4 * trials**2))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def evaluate_gold_decisions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "abstain": 0, "not_screened": 0}
    misses = []
    for row in rows:
        gold = row["is_valid_case"]
        band = row["confidence_band"]
        if band is None:
            counts["not_screened"] += 1
            if gold:
                counts["fn"] += 1
                misses.append(
                    {
                        "state_id": row["state_id"],
                        "title_or_header": row["title_or_header"],
                        "model_id": row["model_id"],
                        "confidence_band": "NOT_SCREENED",
                        "gold_is_valid_case": True,
                    }
                )
            continue
        if band in {"YELLOW_REVIEW", "RED_ESCALATE"}:
            counts["abstain"] += 1
        predicted_positive = band != "GREEN_CLOSE"
        if predicted_positive and gold:
            counts["tp"] += 1
        elif predicted_positive and not gold:
            counts["fp"] += 1
        elif not predicted_positive and gold:
            counts["fn"] += 1
            misses.append(
                {
                    "state_id": row["state_id"],
                    "title_or_header": row["title_or_header"],
                    "model_id": row["model_id"],
                    "confidence_band": band,
                    "gold_is_valid_case": True,
                }
            )
        else:
            counts["tn"] += 1

    recall_trials = counts["tp"] + counts["fn"]
    precision_trials = counts["tp"] + counts["fp"]
    screened_n = len(rows) - counts["not_screened"]
    recall_interval = wilson_interval(counts["tp"], recall_trials)
    return {
        **counts,
        "gold_n": len(rows),
        "screened_n": screened_n,
        "coverage": screened_n / len(rows) if rows else None,
        "recall": counts["tp"] / recall_trials if recall_trials else None,
        "recall_95_ci": recall_interval,
        "precision": counts["tp"] / precision_trials if precision_trials else None,
        "abstain_rate": counts["abstain"] / screened_n if screened_n else None,
        "misses": misses,
    }


def fetch_gold_decisions(
    connection: Any,
    *,
    gold_set_version: str,
    model_id: str,
    sampler_version: str,
    question_schema_version: int,
    threshold_policy_version: int,
) -> list[dict[str, Any]]:
    if not gold_set_version or not model_id or not sampler_version:
        raise ValueError("gold set and model versions are required")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select gold.state_id, state.title_or_header, gold.is_valid_case,
                   decision.model_id, decision.confidence_band
            from gold_set_labels gold
            join clinical_states state on state.id = gold.state_id
            left join lateral (
              select d.model_id, d.confidence_band
              from sys1_decisions d
              where d.state_id = gold.state_id
                and d.model_id = %s
                and d.sampler_version = %s
                and d.question_schema_version = %s
                and d.threshold_policy_version = %s
              order by d.created_at desc, d.id desc
              limit 1
            ) decision on true
            where gold.gold_set_version = %s
              and state.domain = 'pv_literature'
            order by gold.state_id
            """,
            (
                model_id,
                sampler_version,
                question_schema_version,
                threshold_policy_version,
                gold_set_version,
            ),
        )
        rows = cursor.fetchall()
    return [
        {
            "state_id": row[0],
            "title_or_header": row[1],
            "is_valid_case": row[2],
            "model_id": row[3],
            "confidence_band": row[4],
        }
        for row in rows
    ]


def fetch_screening_log(connection: Any, *, days: int = 7) -> list[dict[str, Any]]:
    if not 1 <= days <= 366:
        raise ValueError("days must be between 1 and 366")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select state.domain, decision.model_id, decision.sampler_version,
                   decision.question_schema_version, decision.threshold_policy_version,
                   count(distinct decision.state_id),
                   count(*) filter (where decision.confidence_band = 'GREEN_CLOSE'),
                   count(*) filter (where decision.confidence_band in ('YELLOW_REVIEW', 'RED_ESCALATE')),
                   count(*) filter (where decision.confidence_band = 'RED_ESCALATE'),
                   round(avg(decision.latency_ms)::numeric, 1)
            from sys1_decisions decision
            join clinical_states state on state.id = decision.state_id
            where decision.created_at >= now() - (%s * interval '1 day')
            group by state.domain, decision.model_id, decision.sampler_version,
                     decision.question_schema_version, decision.threshold_policy_version
            order by state.domain, decision.model_id, decision.sampler_version
            """,
            (days,),
        )
        rows = cursor.fetchall()
    return [
        {
            "domain": row[0],
            "model_id": row[1],
            "sampler_version": row[2],
            "question_schema_version": row[3],
            "threshold_policy_version": row[4],
            "states_screened": row[5],
            "green_close": row[6],
            "reviewed": row[7],
            "red_escalate": row[8],
            "average_latency_ms": float(row[9]) if row[9] is not None else None,
        }
        for row in rows
    ]