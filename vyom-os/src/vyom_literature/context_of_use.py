from __future__ import annotations

"""B1 rule 9: versioned context-of-use records for every System One question.

A question without a context-of-use record cannot ship. This module is the
single source of truth consulted by CI (``python -m vyom_literature.context_of_use
--check``) and by any release tooling that wants to prove every deployed
System One question has an owner, purpose, risk statement, and evaluation
method bound to its ``question_schema_version``.

Records are declarative data — they never call a model or write to the
database. Deterministic code owns enforcement.
"""

import json
import sys
from dataclasses import asdict, dataclass
from typing import Any

from vyom_literature.screening import CRITERIA, SPECIAL_SITUATIONS
from vyom_literature.system_one import (
    HOSPITAL_RCM_QUESTIONS,
    PV_ICSRS_QUESTIONS,
    PV_LITERATURE_QUESTIONS,
    QUESTION_SCHEMA_VERSION,
)

CONTEXT_OF_USE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ContextOfUse:
    """Required metadata for one shipped System One question."""

    domain: str
    question_key: str
    question_schema_version: int
    purpose: str
    risk_if_wrong: str
    evaluation_method: str
    owner: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _c(domain: str, key: str, purpose: str, risk: str, method: str) -> ContextOfUse:
    return ContextOfUse(
        domain=domain,
        question_key=key,
        question_schema_version=QUESTION_SCHEMA_VERSION,
        purpose=purpose,
        risk_if_wrong=risk,
        evaluation_method=method,
        owner="QPPV (Vyom safety operations)",
    )


#: Four-criteria screen questions share one evaluation method: frozen gold-set
#: recall/precision per question on adjudicated labels (/v1/reports/gold/{version}).
_GOLD_EVAL = (
    "Frozen gold set: per-question agreement against adjudicated human labels; "
    "CI gate fails if recall drops below the last released value."
)
_ADMISSIONS_EVAL = (
    "Admissions log sampling: monthly random 10% human re-screen of items the "
    "question routed, plus every disagreement escalated to a safety physician."
)


def _build_records() -> tuple[ContextOfUse, ...]:
    records: list[ContextOfUse] = []

    literature_purposes = {
        "has_identifiable_patient": (
            "Literature four-criteria screen: identifiable patient present.",
            "False positive floods the reviewer queue; false negative hides a reportable case.",
        ),
        "has_identifiable_reporter": (
            "Literature four-criteria screen: identifiable reporter present.",
            "False negative hides a follow-up-able case; false positive wastes reviewer time.",
        ),
        "has_suspect_drug": (
            "Literature four-criteria screen: suspect drug taken before the event.",
            "Temporal inversion accepted as valid creates invalid cases.",
        ),
        "has_adverse_event": (
            "Literature four-criteria screen: adverse event or lack of efficacy.",
            "Missed event suppresses a valid case from the regulatory clock.",
        ),
        "is_serious_event": (
            "Seriousness triage feeding the 7/15-day routing proposal.",
            "Under-serious classification delays expedited reporting.",
        ),
        "study_design": (
            "Context flag so reviewers see whether the source is a case report, "
            "review, or trial rather than treating all text alike.",
            "Review-article prose mistaken for primary case data invents cases.",
        ),
    }
    for key in PV_LITERATURE_QUESTIONS:
        purpose, risk = literature_purposes.get(
            key,
            ("Bounded literature screening signal.", "Misprioritisation delays human review."),
        )
        records.append(_c("pv_literature", key, purpose, risk, _GOLD_EVAL))

    icsr_purposes = {
        "valid_case_four_criteria": (
            "ICSR admission check: the four minimum criteria are met.",
            "Wrong answer either submits non-cases to regulators or misses real ones.",
        ),
        "seriousness_criteria_met": (
            "ICSR seriousness determination feeding expedited-track routing.",
            "Missed seriousness breaches the 15-day clock.",
        ),
        "expectedness": (
            "Proposal only: expectedness relative to reference information.",
            "Incorrect unexpectedness misroutes SUSAR handling.",
        ),
        "claim_submission_route": (
            "Hospital RCM claim preflight route proposal.",
            "Wrong route sends claims to manual review unnecessarily or bypasses checks.",
        ),
        "diagnostic_proof_attached": (
            "Hospital RCM preflight evidence gate probability.",
            "Over-trusted probability auto-passes unsupported claims.",
        ),
    }
    for key in PV_ICSRS_QUESTIONS:
        purpose, risk = icsr_purposes.get(
            key, ("Bounded ICSR triage signal.", "Misprioritisation delays human review.")
        )
        # pv_icsr stays local-only by default; same gold/admissions evaluation.
        records.append(_c("pv_icsr", key, purpose, risk, _ADMISSIONS_EVAL))

    for key in HOSPITAL_RCM_QUESTIONS:
        purpose, risk = icsr_purposes.get(
            key, ("Bounded hospital RCM preflight signal.", "Wrong routing delays claim settlement.")
        )
        records.append(_c("hospital_rcm", key, purpose, risk, _ADMISSIONS_EVAL))

    # Screening prompt questions (triage / second look) are versioned through
    # PROMPT_VERSION but their sub-questions must also carry context-of-use.
    for criterion in CRITERIA:
        records.append(
            _c(
                "screening_triage",
                f"criterion:{criterion}",
                f"Four-criteria element '{criterion}' with verbatim evidence quote.",
                "Ungrounded positive invents case data; ungrounded negative suppresses a case.",
                "Verbatim-quote grounding check (evidence must appear in abstract) "
                "plus frozen gold-set per-element agreement.",
            )
        )
    for situation in SPECIAL_SITUATIONS:
        records.append(
            _c(
                "screening_special",
                f"special_situation:{situation}",
                f"Special-situation flag '{situation}' forcing second-look review.",
                "Missed special situation skips required second pass; false flag adds load.",
                "Second-look trigger audit: every planted special situation in the "
                "gold set must force a second look.",
            )
        )
    return tuple(records)


CONTEXT_OF_USE_RECORDS: tuple[ContextOfUse, ...] = _build_records()


def all_questions() -> dict[str, dict[str, str]]:
    """Every shipped System One/screening question key, grouped by domain."""
    return {
        "pv_literature": {key: "" for key in PV_LITERATURE_QUESTIONS},
        "pv_icsr": {key: "" for key in PV_ICSRS_QUESTIONS},
        "hospital_rcm": {key: "" for key in HOSPITAL_RCM_QUESTIONS},
        "screening_triage": {f"criterion:{c}": "" for c in CRITERIA},
        "screening_special": {f"special_situation:{s}": "" for s in SPECIAL_SITUATIONS},
    }


def missing_context_of_use() -> list[tuple[str, str]]:
    """Questions that ship without a context-of-use record (must be empty)."""
    covered = {(r.domain, r.question_key) for r in CONTEXT_OF_USE_RECORDS}
    missing: list[tuple[str, str]] = []
    for domain, keys in all_questions().items():
        for key in keys:
            if (domain, key) not in covered:
                missing.append((domain, key))
    return missing


def orphan_context_of_use() -> list[tuple[str, str]]:
    """Context-of-use rows pointing at questions that no longer exist."""
    live = {(d, k) for d, keys in all_questions().items() for k in keys}
    return [
        (r.domain, r.question_key)
        for r in CONTEXT_OF_USE_RECORDS
        if (r.domain, r.question_key) not in live
    ]


def dump_records() -> str:
    payload = {
        "context_of_use_schema_version": CONTEXT_OF_USE_SCHEMA_VERSION,
        "question_schema_version": QUESTION_SCHEMA_VERSION,
        "records": [r.as_dict() for r in CONTEXT_OF_USE_RECORDS],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--dump":
        print(dump_records())
        return 0
    missing = missing_context_of_use()
    orphans = orphan_context_of_use()
    if missing:
        for domain, key in missing:
            print(f"context-of-use MISSING: {domain}/{key}", file=sys.stderr)
    if orphans:
        for domain, key in orphans:
            print(f"context-of-use ORPHANED (question removed?): {domain}/{key}", file=sys.stderr)
    if missing or orphans:
        print(
            "Rule 9: a System One question without a versioned context-of-use "
            "record cannot ship. Fix context_of_use.py before merging.",
            file=sys.stderr,
        )
        return 1
    print(
        f"context-of-use OK: {len(CONTEXT_OF_USE_RECORDS)} records "
        f"cover every shipped question (schema v{QUESTION_SCHEMA_VERSION})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
