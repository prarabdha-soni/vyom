"""Structured case payload (``vyom.case.v1``).

One schema for AI proposals, human edits and stored versions. Unknown fields
are rejected; partial dates (``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD``) are
allowed, as in ICH E2B(R3).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CASE_SCHEMA_ID = "vyom.case.v1"

ReportType = Literal["spontaneous", "literature", "study", "other"]
AgeUnit = Literal["years", "months", "weeks", "days"]
AgeGroup = Literal["neonate", "infant", "child", "adolescent", "adult", "elderly"]
Sex = Literal["female", "male", "unknown"]
Qualification = Literal[
    "physician", "pharmacist", "other_health_professional", "lawyer", "consumer", "unknown"
]
ProductRole = Literal["suspect", "concomitant", "interacting"]
ActionTaken = Literal[
    "withdrawn", "dose_reduced", "dose_increased", "not_changed", "unknown", "not_applicable"
]
Outcome = Literal[
    "recovered", "recovering", "not_recovered", "recovered_with_sequelae", "fatal", "unknown"
]
SeriousCriterion = Literal[
    "death",
    "life_threatening",
    "hospitalisation",
    "disability",
    "congenital_anomaly",
    "other_medically_important",
]
SpecialSituationKind = Literal[
    "pregnancy",
    "breastfeeding",
    "paediatric",
    "elderly",
    "overdose",
    "abuse_misuse",
    "off_label",
    "medication_error",
    "occupational_exposure",
    "lack_of_efficacy",
]
Challenge = Literal["positive", "negative", "unknown", "not_applicable"]
CausalityCategory = Literal["certain", "probable", "possible", "unlikely", "conditional", "unassessable"]

SERIOUS_CRITERIA: tuple[str, ...] = (
    "death",
    "life_threatening",
    "hospitalisation",
    "disability",
    "congenital_anomaly",
    "other_medically_important",
)
CAUSALITY_CATEGORIES: tuple[str, ...] = (
    "certain",
    "probable",
    "possible",
    "unlikely",
    "conditional",
    "unassessable",
)

_PARTIAL_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


def validate_partial_date(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    match = _PARTIAL_DATE.match(value)
    if not match:
        raise ValueError("dates must be YYYY, YYYY-MM or YYYY-MM-DD")
    year, month, day = match.groups()
    if not 1900 <= int(year) <= 2100:
        raise ValueError("year out of range")
    if month and not 1 <= int(month) <= 12:
        raise ValueError("month out of range")
    if day:
        date(int(year), int(month), int(day))  # raises for impossible dates
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidence(_Strict):
    quote: str = Field(max_length=1000)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    status: Literal["verified", "unverified"] = "verified"


class Patient(_Strict):
    initials: str | None = Field(default=None, max_length=10)
    age_value: float | None = Field(default=None, ge=0, le=150)
    age_unit: AgeUnit | None = None
    age_group: AgeGroup | None = None
    sex: Sex = "unknown"
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    pregnant: bool | None = None


class Reporter(_Strict):
    qualification: Qualification = "unknown"
    country: str | None = Field(default=None, max_length=60)
    identifiable: bool = False
    description: str | None = Field(default=None, max_length=200)


class CaseProduct(_Strict):
    name: str = Field(min_length=1, max_length=200)
    product_code: str | None = Field(default=None, max_length=64)
    role: ProductRole = "suspect"
    dose: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=60)
    indication: str | None = Field(default=None, max_length=200)
    start_date: str | None = None
    stop_date: str | None = None
    action_taken: ActionTaken = "unknown"

    _dates = field_validator("start_date", "stop_date")(validate_partial_date)


class Coding(_Strict):
    dictionary: str | None = Field(default=None, max_length=40)
    soc: str | None = Field(default=None, max_length=120)
    pt: str | None = Field(default=None, max_length=200)
    pt_code: str | None = Field(default=None, max_length=20)
    llt: str | None = Field(default=None, max_length=200)
    llt_code: str | None = Field(default=None, max_length=20)
    status: Literal["none", "suggested", "confirmed"] = "none"


class Causality(_Strict):
    category: CausalityCategory | None = None
    method: Literal["WHO-UMC"] = "WHO-UMC"
    comment: str | None = Field(default=None, max_length=1000)
    assessed_by: str | None = Field(default=None, max_length=64)
    assessed_at: str | None = Field(default=None, max_length=40)


class Reaction(_Strict):
    verbatim: str = Field(min_length=1, max_length=300)
    onset_date: str | None = None
    outcome: Outcome = "unknown"
    serious_criteria: list[SeriousCriterion] = Field(default_factory=list, max_length=6)
    coding: Coding = Field(default_factory=Coding)
    causality: Causality = Field(default_factory=Causality)

    _onset = field_validator("onset_date")(validate_partial_date)

    @field_validator("serious_criteria")
    @classmethod
    def _unique_criteria(cls, value: list[str]) -> list[str]:
        return sorted(set(value), key=SERIOUS_CRITERIA.index)


class SpecialSituation(_Strict):
    kind: SpecialSituationKind


class Narrative(_Strict):
    text: str = Field(default="", max_length=20000)
    status: Literal["empty", "ai_draft", "edited"] = "empty"
    citations: list[str] = Field(default_factory=list, max_length=40)


class CasePayload(_Strict):
    schema_id: Literal["vyom.case.v1"] = CASE_SCHEMA_ID
    report_type: ReportType = "spontaneous"
    patient: Patient = Field(default_factory=Patient)
    reporter: Reporter = Field(default_factory=Reporter)
    products: list[CaseProduct] = Field(default_factory=list, max_length=20)
    reactions: list[Reaction] = Field(default_factory=list, max_length=30)
    special_situations: list[SpecialSituation] = Field(default_factory=list, max_length=10)
    medical_history: list[str] = Field(default_factory=list, max_length=30)
    dechallenge: Challenge = "unknown"
    rechallenge: Challenge = "unknown"
    narrative: Narrative = Field(default_factory=Narrative)
    literature_reference: str | None = Field(default=None, max_length=600)
    evidence: dict[str, Evidence] = Field(default_factory=dict)

    @field_validator("medical_history")
    @classmethod
    def _history_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if any(len(item) > 200 for item in cleaned):
            raise ValueError("medical history items are limited to 200 characters")
        return cleaned

    @field_validator("evidence")
    @classmethod
    def _evidence_keys(cls, value: dict[str, Evidence]) -> dict[str, Evidence]:
        if len(value) > 120:
            raise ValueError("too many evidence entries")
        for key in value:
            if not re.fullmatch(r"[a-z_]+(\.\d+)?(\.[a-z_]+)?", key):
                raise ValueError(f"invalid evidence key: {key}")
        return value

    @field_validator("special_situations")
    @classmethod
    def _unique_situations(cls, value: list[SpecialSituation]) -> list[SpecialSituation]:
        seen: dict[str, SpecialSituation] = {}
        for item in value:
            seen.setdefault(item.kind, item)
        return list(seen.values())
