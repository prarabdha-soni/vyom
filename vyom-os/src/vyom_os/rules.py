"""Deterministic case rules: validity, seriousness, expectedness, clock, duplicates.

Pure functions over the case payload. Models propose field values; these
rules decide what the values mean. Every result carries ``RULES_VERSION`` so
a stored assessment can be reproduced.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from vyom_os.models import CasePayload

RULES_VERSION = "case-rules.v1"
DEFAULT_CLOCK_POLICY: dict[str, Any] = {"version": "clock.v1", "serious_days": 15, "non_serious_days": 90}
DUE_SOON_DAYS = 3


def normalise_term(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    return re.sub(r"\s+", " ", cleaned)


def validity(payload: CasePayload) -> dict[str, Any]:
    """ICH minimum criteria for a valid individual case safety report."""
    patient = payload.patient
    criteria = {
        "identifiable_patient": any(
            (
                patient.initials,
                patient.age_value is not None,
                patient.age_group,
                patient.sex != "unknown",
                patient.pregnant is not None,
            )
        ),
        "identifiable_reporter": payload.reporter.identifiable,
        "suspect_product": any(product.role == "suspect" for product in payload.products),
        "adverse_event": bool(payload.reactions),
    }
    missing = [name for name, met in criteria.items() if not met]
    return {"valid": not missing, "criteria": criteria, "missing": missing}


def seriousness(payload: CasePayload) -> dict[str, Any]:
    criteria = sorted({criterion for reaction in payload.reactions for criterion in reaction.serious_criteria})
    fatal = any(reaction.outcome == "fatal" for reaction in payload.reactions)
    if fatal and "death" not in criteria:
        criteria = sorted({*criteria, "death"})
    return {"serious": bool(criteria), "criteria": criteria}


def expectedness(payload: CasePayload, reference_terms: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Compare each reaction with the product's reference safety information.

    Without licensed coding this is a text match on the verbatim and any
    suggested preferred term, so a reviewer must confirm it.
    """
    listed = {normalise_term(str(item.get("term", ""))) for item in (reference_terms or []) if item.get("term")}
    results = []
    for index, reaction in enumerate(payload.reactions):
        candidates = {normalise_term(reaction.verbatim)}
        if reaction.coding.pt:
            candidates.add(normalise_term(reaction.coding.pt))
        if reaction.coding.llt:
            candidates.add(normalise_term(reaction.coding.llt))
        if reference_terms is None:
            results.append({"index": index, "expected": None, "basis": "no reference safety information"})
            continue
        matched = sorted(term for term in candidates if term and (term in listed or any(term in item or item in term for item in listed if item)))
        coded = reaction.coding.status == "confirmed" and bool(reaction.coding.pt)
        results.append(
            {
                "index": index,
                "expected": bool(matched),
                "basis": ("coded term" if coded else "text match — confirm") if matched else "not listed",
            }
        )
    return results


def clock(
    day_zero: date,
    serious: bool,
    policy: dict[str, Any] | None,
    today: date,
    *,
    closed: bool = False,
) -> dict[str, Any]:
    policy = {**DEFAULT_CLOCK_POLICY, **(policy or {})}
    deadline_days = int(policy["serious_days"] if serious else policy["non_serious_days"])
    due = day_zero + timedelta(days=deadline_days)
    elapsed = (today - day_zero).days
    remaining = (due - today).days
    if closed:
        status = "stopped"
    elif remaining < 0:
        status = "overdue"
    elif remaining <= DUE_SOON_DAYS:
        status = "due_soon"
    else:
        status = "on_track"
    return {
        "policy_version": str(policy.get("version", "clock.v1")),
        "day_zero": day_zero.isoformat(),
        "deadline_days": deadline_days,
        "due_date": due.isoformat(),
        "days_elapsed": elapsed,
        "days_remaining": remaining,
        "status": status,
        "label": "Stopped" if closed else f"Day {max(elapsed, 0)} of {deadline_days}",
    }


def follow_up(payload: CasePayload, validity_result: dict[str, Any]) -> dict[str, Any]:
    missing = list(validity_result["missing"])
    if payload.reactions and any(r.outcome == "unknown" for r in payload.reactions):
        missing.append("reaction_outcome")
    if payload.products and all(p.start_date is None for p in payload.products if p.role == "suspect"):
        missing.append("therapy_dates")
    if payload.reactions and all(r.onset_date is None for r in payload.reactions):
        missing.append("onset_date")
    return {"required": bool(missing), "items": missing}


def assess(
    payload: CasePayload,
    *,
    reference_terms: list[dict[str, Any]] | None,
    day_zero: date,
    clock_policy: dict[str, Any] | None,
    today: date,
    closed: bool = False,
) -> dict[str, Any]:
    valid = validity(payload)
    serious = seriousness(payload)
    expected = expectedness(payload, reference_terms)
    unexpected_serious = serious["serious"] and any(item["expected"] is False for item in expected)
    return {
        "rules_version": RULES_VERSION,
        "validity": valid,
        "seriousness": serious,
        "expectedness": expected,
        "expedited_candidate": unexpected_serious,
        "clock": clock(day_zero, serious["serious"], clock_policy, today, closed=closed),
        "follow_up": follow_up(payload, valid),
        "causality_complete": bool(payload.reactions)
        and all(r.causality.category is not None for r in payload.reactions),
    }


def _age_years(payload: CasePayload) -> float | None:
    patient = payload.patient
    if patient.age_value is None:
        return None
    factor = {"years": 1, "months": 1 / 12, "weeks": 1 / 52, "days": 1 / 365, None: 1}[patient.age_unit]
    return patient.age_value * factor


def duplicate_score(candidate: CasePayload, other: CasePayload) -> tuple[float, list[str]]:
    """Heuristic similarity of two cases. A human confirms or rules out."""
    reasons: list[str] = []
    score = 0.0
    a_products = {(p.product_code or normalise_term(p.name)) for p in candidate.products if p.role == "suspect"}
    b_products = {(p.product_code or normalise_term(p.name)) for p in other.products if p.role == "suspect"}
    if not a_products & b_products:
        return 0.0, []
    score += 0.3
    reasons.append("same suspect product")

    a_events = {normalise_term(r.coding.pt or r.verbatim) for r in candidate.reactions}
    b_events = {normalise_term(r.coding.pt or r.verbatim) for r in other.reactions}
    if any(a and b and (a in b or b in a) for a in a_events for b in b_events):
        score += 0.3
        reasons.append("same reported event")

    pa, pb = candidate.patient, other.patient
    if pa.sex != "unknown" and pa.sex == pb.sex:
        score += 0.1
        reasons.append("same sex")
    age_a, age_b = _age_years(candidate), _age_years(other)
    if age_a is not None and age_b is not None and abs(age_a - age_b) <= 1:
        score += 0.15
        reasons.append("age within one year")
    if pa.initials and pb.initials and pa.initials.replace(".", "").casefold() == pb.initials.replace(".", "").casefold():
        score += 0.15
        reasons.append("same initials")

    onset_a = {r.onset_date[:7] for r in candidate.reactions if r.onset_date and len(r.onset_date) >= 7}
    onset_b = {r.onset_date[:7] for r in other.reactions if r.onset_date and len(r.onset_date) >= 7}
    if onset_a & onset_b:
        score += 0.1
        reasons.append("onset in the same month")
    return round(min(score, 1.0), 2), reasons


DUPLICATE_THRESHOLD = 0.75
