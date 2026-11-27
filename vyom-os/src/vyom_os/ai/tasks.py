"""Task contracts for model calls and the validators that gate their output.

Each task has a pinned version, a structured-output schema (the OpenAPI
subset Gemini accepts as ``responseSchema``) and an application-owned
validator. Output that fails validation never reaches a reviewer as fact:
evidence that cannot be found in the source is marked unverified, and
malformed output raises so the caller fails closed to manual entry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from vyom_os.models import (
    SERIOUS_CRITERIA,
    CaseProduct,
    CasePayload,
    Evidence,
    Narrative,
    Patient,
    Reaction,
    Reporter,
    SpecialSituation,
    validate_partial_date,
)


class AiOutputError(ValueError):
    """Model output broke the contract. The caller fails closed."""


@dataclass(frozen=True)
class AiTask:
    name: str
    version: str
    call_kind: Literal["system_one", "system_two"]
    system_instruction: str
    response_schema: dict[str, Any]


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {**schema, "nullable": True}


_STR = {"type": "string"}
_EVIDENCE = _nullable({"type": "string", "description": "Exact quote from the source text"})

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "report_type": {"type": "string", "enum": ["spontaneous", "literature", "study", "other"]},
        "patient": {
            "type": "object",
            "properties": {
                "initials": _nullable(_STR),
                "age_value": _nullable({"type": "number"}),
                "age_unit": _nullable({"type": "string", "enum": ["years", "months", "weeks", "days"]}),
                "age_group": _nullable(
                    {"type": "string", "enum": ["neonate", "infant", "child", "adolescent", "adult", "elderly"]}
                ),
                "sex": {"type": "string", "enum": ["female", "male", "unknown"]},
                "weight_kg": _nullable({"type": "number"}),
                "pregnant": _nullable({"type": "boolean"}),
                "evidence": _EVIDENCE,
            },
            "required": ["sex"],
        },
        "reporter": {
            "type": "object",
            "properties": {
                "qualification": {
                    "type": "string",
                    "enum": ["physician", "pharmacist", "other_health_professional", "lawyer", "consumer", "unknown"],
                },
                "country": _nullable(_STR),
                "identifiable": {"type": "boolean"},
                "description": _nullable(_STR),
                "evidence": _EVIDENCE,
            },
            "required": ["qualification", "identifiable"],
        },
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": _STR,
                    "role": {"type": "string", "enum": ["suspect", "concomitant", "interacting"]},
                    "dose": _nullable(_STR),
                    "route": _nullable(_STR),
                    "indication": _nullable(_STR),
                    "start_date": _nullable(_STR),
                    "stop_date": _nullable(_STR),
                    "action_taken": {
                        "type": "string",
                        "enum": ["withdrawn", "dose_reduced", "dose_increased", "not_changed", "unknown", "not_applicable"],
                    },
                    "evidence": _EVIDENCE,
                },
                "required": ["name", "role", "action_taken"],
            },
        },
        "reactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "verbatim": _STR,
                    "onset_date": _nullable(_STR),
                    "outcome": {
                        "type": "string",
                        "enum": ["recovered", "recovering", "not_recovered", "recovered_with_sequelae", "fatal", "unknown"],
                    },
                    "serious_criteria": {"type": "array", "items": {"type": "string", "enum": list(SERIOUS_CRITERIA)}},
                    "evidence": _EVIDENCE,
                },
                "required": ["verbatim", "outcome", "serious_criteria"],
            },
        },
        "special_situations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "pregnancy", "breastfeeding", "paediatric", "elderly", "overdose", "abuse_misuse",
                            "off_label", "medication_error", "occupational_exposure", "lack_of_efficacy",
                        ],
                    },
                    "evidence": _EVIDENCE,
                },
                "required": ["kind"],
            },
        },
        "medical_history": {"type": "array", "items": _STR},
        "dechallenge": {"type": "string", "enum": ["positive", "negative", "unknown", "not_applicable"]},
        "rechallenge": {"type": "string", "enum": ["positive", "negative", "unknown", "not_applicable"]},
        "summary": _STR,
    },
    "required": [
        "report_type", "patient", "reporter", "products", "reactions", "special_situations",
        "medical_history", "dechallenge", "rechallenge", "summary",
    ],
}

NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": _STR,
        "citations": {"type": "array", "items": _STR},
    },
    "required": ["narrative", "citations"],
}

REPORT_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": _STR,
        "citations": {"type": "array", "items": _STR},
    },
    "required": ["text", "citations"],
}

CASE_EXTRACTION = AiTask(
    name="case_extraction",
    version="case-extract.v1",
    call_kind="system_one",
    system_instruction=(
        "You extract pharmacovigilance case data from one source document so a drug-safety associate can "
        "review it. Use only the supplied text and never infer facts that are not stated. Copy every "
        "'evidence' value verbatim from source_text: an exact substring of at most 300 characters. Record "
        "each distinct adverse event once, in the reporter's own words. Add a seriousness criterion only when "
        "the text supports it. Use null or 'unknown' when information is absent. Write dates as YYYY-MM-DD, "
        "YYYY-MM or YYYY. Products in context.tenant_products belong to the company; mark a product 'suspect' "
        "only when it is the product under report or the reporter suspects it. Do not assess causality: that "
        "is a physician's decision."
    ),
    response_schema=EXTRACTION_SCHEMA,
)

CASE_NARRATIVE = AiTask(
    name="case_narrative",
    version="case-narrative.v1",
    call_kind="system_two",
    system_instruction=(
        "Write the narrative for one individual case safety report in the usual order: source and reporter, "
        "patient, relevant history, suspect product and therapy, events with onset and course, treatment, "
        "seriousness, outcome, dechallenge and rechallenge. Use only facts in case_data or source_text and write "
        "'not reported' instead of guessing. Do not state a causality conclusion. Use plain clinical English in "
        "the past tense with Indian English spelling. In 'citations', return short exact quotes from "
        "source_text that support the key facts."
    ),
    response_schema=NARRATIVE_SCHEMA,
)

REPORT_SECTION = AiTask(
    name="report_section",
    version="report-section.v1",
    call_kind="system_two",
    system_instruction=(
        "Draft one section of a periodic safety report from the supplied data only. Use numbers exactly as they "
        "appear in the data; do not compute new rates or reach benefit-risk conclusions the data do not support. "
        "Refer to cases by case number and to articles by identifier. If the data are not enough, say which "
        "input the safety team must provide. In 'citations', list the case numbers and literature identifiers "
        "you referred to. Use Indian English spelling."
    ),
    response_schema=REPORT_SECTION_SCHEMA,
)

TASKS = {task.name: task for task in (CASE_EXTRACTION, CASE_NARRATIVE, REPORT_SECTION)}


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def locate(quote: str | None, source: str) -> Evidence | None:
    """Find an evidence quote in the source; unverified if it is not there."""
    if not quote or not quote.strip():
        return None
    quote = quote.strip()[:1000]
    index = source.find(quote)
    if index < 0:
        index = source.casefold().find(quote.casefold())
    if index >= 0:
        return Evidence(quote=quote, start=index, end=index + len(quote), status="verified")
    # Whitespace-insensitive fallback: map the squashed match back to offsets.
    pattern = r"\s+".join(re.escape(part) for part in quote.split())
    match = re.search(pattern, source, flags=re.IGNORECASE) if pattern else None
    if match:
        return Evidence(quote=source[match.start():match.end()], start=match.start(), end=match.end(), status="verified")
    return Evidence(quote=quote, start=None, end=None, status="unverified")


def _age_group(age_value: float | None, unit: str | None) -> str | None:
    if age_value is None:
        return None
    years = age_value * {"years": 1, "months": 1 / 12, "weeks": 1 / 52, "days": 1 / 365, None: 1}[unit]
    if years < 28 / 365:
        return "neonate"
    if years < 2:
        return "infant"
    if years < 12:
        return "child"
    if years < 18:
        return "adolescent"
    if years < 65:
        return "adult"
    return "elderly"


def _safe_date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return validate_partial_date(value.strip())
    except ValueError:
        return None


def match_product(name: str, tenant_products: list[dict[str, Any]]) -> str | None:
    folded = name.casefold()
    for product in tenant_products:
        code = str(product.get("code", ""))
        if code and code.casefold() in folded:
            return code
    for product in tenant_products:
        for key in ("name", "active_ingredient"):
            value = str(product.get(key) or "").casefold()
            if value and (value in folded or folded in value):
                return str(product.get("code"))
    return None


@dataclass
class ExtractionResult:
    payload: CasePayload
    warnings: list[str] = field(default_factory=list)


def parse_extraction(
    output: Any,
    *,
    source_text: str,
    tenant_products: list[dict[str, Any]],
    channel: str,
) -> ExtractionResult:
    if not isinstance(output, dict):
        raise AiOutputError("extraction output is not an object")
    warnings: list[str] = []
    evidence: dict[str, Evidence] = {}

    def keep(path: str, quote: Any) -> None:
        located = locate(quote if isinstance(quote, str) else None, source_text)
        if located is None:
            return
        if located.status == "unverified":
            warnings.append(f"Evidence for {path} was not found in the source; confirm it by hand.")
        evidence[path] = located

    try:
        raw_patient = output.get("patient") or {}
        age_value = raw_patient.get("age_value")
        age_unit = raw_patient.get("age_unit") if age_value is not None else None
        patient = Patient(
            initials=(raw_patient.get("initials") or None),
            age_value=age_value,
            age_unit=age_unit or ("years" if age_value is not None else None),
            age_group=raw_patient.get("age_group") or _age_group(age_value, age_unit or "years"),
            sex=raw_patient.get("sex") or "unknown",
            weight_kg=raw_patient.get("weight_kg"),
            pregnant=raw_patient.get("pregnant"),
        )
        keep("patient", raw_patient.get("evidence"))

        raw_reporter = output.get("reporter") or {}
        reporter = Reporter(
            qualification=raw_reporter.get("qualification") or "unknown",
            country=raw_reporter.get("country") or None,
            identifiable=bool(raw_reporter.get("identifiable")),
            description=(raw_reporter.get("description") or None),
        )
        keep("reporter", raw_reporter.get("evidence"))

        products = []
        for index, raw in enumerate(output.get("products") or []):
            if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
                continue
            name = str(raw["name"]).strip()[:200]
            products.append(
                CaseProduct(
                    name=name,
                    product_code=match_product(name, tenant_products),
                    role=raw.get("role") or "suspect",
                    dose=(raw.get("dose") or None),
                    route=(raw.get("route") or None),
                    indication=(raw.get("indication") or None),
                    start_date=_safe_date(raw.get("start_date")),
                    stop_date=_safe_date(raw.get("stop_date")),
                    action_taken=raw.get("action_taken") or "unknown",
                )
            )
            keep(f"products.{len(products) - 1}", raw.get("evidence"))
            if index >= 19:
                break

        reactions = []
        for raw in output.get("reactions") or []:
            if not isinstance(raw, dict) or not str(raw.get("verbatim") or "").strip():
                continue
            criteria = [c for c in (raw.get("serious_criteria") or []) if c in SERIOUS_CRITERIA]
            reactions.append(
                Reaction(
                    verbatim=str(raw["verbatim"]).strip()[:300],
                    onset_date=_safe_date(raw.get("onset_date")),
                    outcome=raw.get("outcome") or "unknown",
                    serious_criteria=criteria,
                )
            )
            keep(f"reactions.{len(reactions) - 1}", raw.get("evidence"))
            if len(reactions) >= 30:
                break

        situations = []
        for raw in output.get("special_situations") or []:
            if isinstance(raw, dict) and raw.get("kind"):
                situations.append(SpecialSituation(kind=raw["kind"]))
                keep(f"special_situations.{len(situations) - 1}", raw.get("evidence"))
        derived_group = patient.age_group
        kinds = {item.kind for item in situations}
        if derived_group in {"neonate", "infant", "child", "adolescent"} and "paediatric" not in kinds:
            situations.append(SpecialSituation(kind="paediatric"))
        if derived_group == "elderly" and "elderly" not in kinds:
            situations.append(SpecialSituation(kind="elderly"))
        if patient.pregnant and "pregnancy" not in kinds:
            situations.append(SpecialSituation(kind="pregnancy"))

        history = [str(item).strip()[:200] for item in (output.get("medical_history") or []) if str(item).strip()]
        payload = CasePayload(
            report_type=output.get("report_type") or ("literature" if channel == "literature" else "spontaneous"),
            patient=patient,
            reporter=reporter,
            products=products,
            reactions=reactions,
            special_situations=situations[:10],
            medical_history=history[:30],
            dechallenge=output.get("dechallenge") or "unknown",
            rechallenge=output.get("rechallenge") or "unknown",
            narrative=Narrative(),
            evidence=evidence,
        )
    except ValidationError as error:
        raise AiOutputError(f"extraction output failed validation: {error.error_count()} errors") from error

    if not any(p.product_code for p in payload.products if p.role == "suspect"):
        warnings.append("No suspect product matched a product in this tenant's catalogue.")
    return ExtractionResult(payload=payload, warnings=warnings)


def parse_narrative(output: Any, *, source_text: str) -> tuple[str, list[str], list[str]]:
    if not isinstance(output, dict):
        raise AiOutputError("narrative output is not an object")
    text = output.get("narrative")
    citations = output.get("citations")
    if not isinstance(text, str) or len(text.strip()) < 40:
        raise AiOutputError("narrative is missing or too short")
    if not isinstance(citations, list):
        raise AiOutputError("citations must be a list")
    verified, warnings = [], []
    for quote in citations[:40]:
        if not isinstance(quote, str):
            continue
        located = locate(quote, source_text)
        if located and located.status == "verified":
            verified.append(located.quote)
        else:
            warnings.append(f"Citation not found in the source: “{quote[:80]}”")
    if not verified:
        warnings.append("The draft has no citation that matches the source text. Check every fact.")
    return text.strip()[:20000], verified, warnings


_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")


def parse_report_section(
    output: Any, *, allowed_refs: set[str], allowed_numbers: set[str]
) -> tuple[str, list[str], list[str]]:
    if not isinstance(output, dict):
        raise AiOutputError("section output is not an object")
    text = output.get("text")
    citations = output.get("citations")
    if not isinstance(text, str) or not text.strip():
        raise AiOutputError("section text is missing")
    if not isinstance(citations, list):
        raise AiOutputError("citations must be a list")
    warnings = []
    kept = [ref for ref in citations if isinstance(ref, str) and ref in allowed_refs]
    unknown = [ref for ref in citations if isinstance(ref, str) and ref not in allowed_refs]
    if unknown:
        warnings.append(f"Removed citations that are not in the report data: {', '.join(unknown[:5])}")
    stray = sorted({n for n in _NUMBER.findall(text) if n not in allowed_numbers})
    if stray:
        warnings.append(f"Numbers not found in the report data: {', '.join(stray[:8])}. Verify before sign-off.")
    for ref in re.findall(r"VY-(?:CASE|LIT)-\d{4}", text):
        if ref not in allowed_refs:
            warnings.append(f"{ref} is not part of this report's data.")
    return text.strip()[:12000], kept, warnings
