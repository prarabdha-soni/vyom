"""Draft export of an approved case, organised by ICH E2B(R3) data elements.

This is a reviewable data-element document, not an HL7 ICSR message: it is
not ready for submission through a regulatory gateway. It gives the safety
team every value they need, under the E2B(R3) element numbers, with the
code lists E2B uses.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from vyom_os import audit
from vyom_os.cases import _current, _head  # noqa: PLC2701 - same bounded context
from vyom_os.core import Conflict, Ctx, NotFound
from vyom_os.db import fetch_one, fetch_value
from vyom_os.models import CasePayload

FORMAT = "e2b_r3_data_elements_xml"
NAMESPACE = "urn:vyom:icsr-draft:1"
NOTICE = (
    "Draft organised by ICH E2B(R3) data element. Not an HL7 ICSR message and not ready "
    "for gateway submission. Review against the source before use."
)

_REPORT_TYPE = {"spontaneous": "1", "literature": "1", "study": "2", "other": "3"}
_QUALIFICATION = {
    "physician": "1", "pharmacist": "2", "other_health_professional": "3", "lawyer": "4", "consumer": "5",
}
_AGE_UNIT = {"years": "a", "months": "mo", "weeks": "wk", "days": "d"}
_AGE_GROUP = {"neonate": "1", "infant": "2", "child": "3", "adolescent": "4", "adult": "5", "elderly": "6"}
_SEX = {"male": "1", "female": "2"}
_OUTCOME = {
    "recovered": "1", "recovering": "2", "not_recovered": "3", "recovered_with_sequelae": "4", "fatal": "5", "unknown": "0",
}
_ROLE = {"suspect": "1", "concomitant": "2", "interacting": "3"}
_ACTION = {
    "withdrawn": "1", "dose_reduced": "2", "dose_increased": "3", "not_changed": "4", "unknown": "0", "not_applicable": "9",
}
_SERIOUS = (
    ("E.i.3.2a", "Results in death", "death"),
    ("E.i.3.2b", "Life threatening", "life_threatening"),
    ("E.i.3.2c", "Caused / prolonged hospitalisation", "hospitalisation"),
    ("E.i.3.2d", "Disabling / incapacitating", "disability"),
    ("E.i.3.2e", "Congenital anomaly / birth defect", "congenital_anomaly"),
    ("E.i.3.2f", "Other medically important condition", "other_medically_important"),
)
_COUNTRIES = {
    "India": "IN", "Nepal": "NP", "Sri Lanka": "LK", "Bangladesh": "BD", "United Kingdom": "GB",
    "United States": "US", "Germany": "DE", "France": "FR", "Kenya": "KE", "South Africa": "ZA", "Brazil": "BR",
}


def e2b_date(value: str | None) -> str | None:
    """YYYY-MM-DD / YYYY-MM / YYYY -> YYYYMMDD / YYYYMM / YYYY."""
    return value.replace("-", "") if value else None


def _element(parent: ET.Element, element_id: str, name: str, value: Any = None, *, null: str = "UNK") -> ET.Element:
    node = ET.SubElement(parent, "element", {"id": element_id, "name": name})
    if value is None or value == "":
        node.set("nullFlavor", null)
    else:
        node.text = str(value).lower() if isinstance(value, bool) else str(value)
    return node


def build_xml(
    *,
    case_number: str,
    version: int,
    payload: CasePayload,
    assessment: dict[str, Any],
    day_zero: str,
    latest_info: str,
    sender_name: str,
    tenant_slug: str,
    generated_at: datetime,
) -> str:
    country = _COUNTRIES.get(payload.reporter.country or "", "")
    root = ET.Element(
        "icsrDraft",
        {
            "xmlns": NAMESPACE,
            "caseNumber": case_number,
            "caseVersion": str(version),
            "generatedAt": generated_at.isoformat(timespec="seconds"),
            "rulesVersion": str(assessment.get("rules_version")),
        },
    )
    ET.SubElement(root, "notice").text = NOTICE

    section_c = ET.SubElement(root, "section", {"id": "C", "name": "Identification of the case safety report"})
    _element(section_c, "C.1.1", "Sender's (case) safety report unique identifier",
             f"{country or 'XX'}-{tenant_slug.upper()}-{case_number}")
    _element(section_c, "C.1.2", "Date of creation", generated_at.strftime("%Y%m%d%H%M%S+0000"))
    _element(section_c, "C.1.3", "Type of report", _REPORT_TYPE[payload.report_type])
    _element(section_c, "C.1.4", "Date report was first received from source", e2b_date(day_zero))
    _element(section_c, "C.1.5", "Date of most recent information for this report", e2b_date(latest_info))
    _element(section_c, "C.1.7", "Does this case fulfil the local criteria for an expedited report?",
             bool(assessment.get("expedited_candidate")))
    reporter = ET.SubElement(section_c, "item", {"id": "C.2.r", "index": "1", "name": "Primary source(s) of information"})
    _element(reporter, "C.2.r.3", "Reporter's country code", country or None)
    _element(reporter, "C.2.r.4", "Qualification", _QUALIFICATION.get(payload.reporter.qualification))
    _element(reporter, "C.2.r.5", "Primary source for regulatory purposes", "1")
    _element(section_c, "C.3.1", "Sender type", "1")
    _element(section_c, "C.3.2", "Sender's organisation", sender_name)
    if payload.literature_reference:
        literature = ET.SubElement(section_c, "item", {"id": "C.4.r", "index": "1", "name": "Literature reference(s)"})
        _element(literature, "C.4.r.1", "Literature reference(s)", payload.literature_reference)

    patient = payload.patient
    section_d = ET.SubElement(root, "section", {"id": "D", "name": "Patient characteristics"})
    _element(section_d, "D.1", "Patient (name or initials)", patient.initials)
    _element(section_d, "D.2.2a", "Age at time of onset of reaction / event (number)",
             (int(patient.age_value) if patient.age_value is not None and float(patient.age_value).is_integer() else patient.age_value))
    _element(section_d, "D.2.2b", "Age at time of onset of reaction / event (unit)", _AGE_UNIT.get(patient.age_unit or ""))
    _element(section_d, "D.2.3", "Patient age group", _AGE_GROUP.get(patient.age_group or ""))
    _element(section_d, "D.3", "Body weight (kg)", patient.weight_kg)
    _element(section_d, "D.5", "Sex", _SEX.get(patient.sex))
    _element(section_d, "D.7.2", "Text for relevant medical history and concurrent conditions",
             "; ".join(payload.medical_history) or None)

    section_e = ET.SubElement(root, "section", {"id": "E", "name": "Reaction(s) / event(s)"})
    for index, reaction in enumerate(payload.reactions, start=1):
        item = ET.SubElement(section_e, "item", {"id": "E.i", "index": str(index)})
        _element(item, "E.i.1.1a", "Reaction / event as reported by the primary source", reaction.verbatim)
        coded = reaction.coding.status == "confirmed" and reaction.coding.llt_code
        _element(item, "E.i.2.1a", "MedDRA version for reaction / event",
                 reaction.coding.dictionary if coded else None, null="NA" if not coded else "UNK")
        _element(item, "E.i.2.1b", "Reaction / event (MedDRA code)",
                 reaction.coding.llt_code if coded else None, null="NA" if not coded else "UNK")
        for element_id, name, criterion in _SERIOUS:
            _element(item, element_id, name, criterion in reaction.serious_criteria)
        _element(item, "E.i.4", "Date of start of reaction / event", e2b_date(reaction.onset_date))
        _element(item, "E.i.7", "Outcome of reaction / event at the time of last observation", _OUTCOME[reaction.outcome])

    section_g = ET.SubElement(root, "section", {"id": "G", "name": "Drug(s) information"})
    for index, product in enumerate(payload.products, start=1):
        item = ET.SubElement(section_g, "item", {"id": "G.k", "index": str(index)})
        _element(item, "G.k.1", "Characterisation of drug role", _ROLE[product.role])
        _element(item, "G.k.2.2", "Medicinal product name as reported by the primary source", product.name)
        _element(item, "G.k.4.r.4", "Date of start of drug", e2b_date(product.start_date))
        _element(item, "G.k.4.r.5", "Date of last administration", e2b_date(product.stop_date))
        _element(item, "G.k.4.r.8", "Dosage text", product.dose)
        _element(item, "G.k.4.r.10.1", "Route of administration (free text)", product.route)
        _element(item, "G.k.7.r.1", "Indication as reported by the primary source", product.indication)
        _element(item, "G.k.8", "Action(s) taken with drug", _ACTION[product.action_taken])
        if product.role == "suspect":
            for r_index, reaction in enumerate(payload.reactions, start=1):
                if reaction.causality.category is None:
                    continue
                assessment_node = ET.SubElement(
                    item, "item", {"id": "G.k.9.i.2.r", "index": str(r_index), "name": "Assessment of relatedness"}
                )
                _element(assessment_node, "G.k.9.i.1", "Reaction(s) / event(s) assessed", f"E.i[{r_index}]")
                _element(assessment_node, "G.k.9.i.2.r.1", "Source of assessment", "Sender (safety physician)")
                _element(assessment_node, "G.k.9.i.2.r.2", "Method of assessment", reaction.causality.method)
                _element(assessment_node, "G.k.9.i.2.r.3", "Result of assessment", reaction.causality.category)

    section_h = ET.SubElement(root, "section", {"id": "H", "name": "Narrative case summary and further information"})
    _element(section_h, "H.1", "Case narrative including clinical course, therapeutic measures, outcome",
             payload.narrative.text or None)
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def export_case(connection: Any, ctx: Ctx, case_number: str) -> dict[str, Any]:
    ctx.require("case.export")
    head = _head(connection, case_number, lock=True)
    if head["status"] != "approved":
        raise Conflict("Only approved cases can be exported.")
    current = _current(connection, head)
    payload = CasePayload.model_validate(current["payload"])
    generated_at = datetime.now(timezone.utc)
    content = build_xml(
        case_number=case_number,
        version=current["version"],
        payload=payload,
        assessment=current["assessments"],
        day_zero=head["day_zero"].isoformat(),
        latest_info=current["created_at"].date().isoformat(),
        sender_name=ctx.tenant.display_name,
        tenant_slug=ctx.tenant.slug,
        generated_at=generated_at,
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    export_id = fetch_value(
        connection,
        """
        insert into case_exports (case_id, case_version, format, content, content_sha256, created_by)
        values (%s, %s, %s, %s, %s, %s) returning id
        """,
        (head["id"], current["version"], FORMAT, content, digest, ctx.actor.user_id),
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number, event_type="e2b_exported", actor=ctx.actor,
        detail={"export_id": export_id, "version": current["version"], "sha256": digest, "format": FORMAT},
    )
    return {"export_id": export_id, "sha256": digest, "version": current["version"]}


def get_export(connection: Any, ctx: Ctx, case_number: str, export_id: int) -> dict[str, Any]:
    ctx.require("case.export")
    row = fetch_one(
        connection,
        """
        select e.id, e.case_version, e.content, e.content_sha256, e.created_at
        from case_exports e join cases c on c.id = e.case_id
        where c.case_number = %s and e.id = %s
        """,
        (case_number, export_id),
    )
    if row is None:
        raise NotFound("No such export.")
    return row
