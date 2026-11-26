import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from vyom_os.ai.tasks import parse_report_section
from vyom_os.e2b import NAMESPACE, build_xml, e2b_date
from vyom_os.models import CasePayload, CaseProduct, Causality, Narrative, Patient, Reaction, Reporter
from vyom_os.reports import progress, to_markdown


def _payload():
    return CasePayload(
        patient=Patient(age_value=62, age_unit="years", age_group="adult", sex="male", initials="R.K."),
        reporter=Reporter(qualification="physician", country="India", identifiable=True),
        products=[CaseProduct(name="VY-201", product_code="VY-201", role="suspect", action_taken="withdrawn", start_date="2026-11")],
        reactions=[Reaction(verbatim="angioedema", onset_date="2026-11-20", outcome="recovered",
                            serious_criteria=["hospitalisation"], causality=Causality(category="probable"))],
        narrative=Narrative(text="A sample narrative for a fictional case.", status="edited"),
    )


def test_e2b_dates_keep_partial_precision():
    assert (e2b_date("2026-11-20"), e2b_date("2026-11"), e2b_date("2026"), e2b_date(None)) == ("20261120", "202611", "2026", None)


def test_e2b_draft_uses_element_numbers_and_code_lists():
    content = build_xml(
        case_number="VY-CASE-0001", version=3, payload=_payload(),
        assessment={"rules_version": "case-rules.v1", "expedited_candidate": True},
        day_zero="2026-11-22", latest_info="2026-11-26", sender_name="Demo Pharma (FICTIONAL)",
        tenant_slug="demo-pharma", generated_at=datetime(2026, 11, 26, tzinfo=timezone.utc),
    )
    root = ET.fromstring(content)
    values = {node.get("id"): node for node in root.iter(f"{{{NAMESPACE}}}element")}
    assert values["C.1.1"].text == "IN-DEMO-PHARMA-VY-CASE-0001"
    assert values["C.1.4"].text == "20261122"
    assert values["C.1.7"].text == "true"
    assert values["C.2.r.4"].text == "1"
    assert values["D.5"].text == "1"
    assert values["E.i.3.2c"].text == "true" and values["E.i.3.2a"].text == "false"
    assert values["E.i.2.1b"].get("nullFlavor") == "NA"
    assert values["G.k.8"].text == "1"
    assert values["G.k.4.r.4"].text == "202611"
    assert values["G.k.9.i.2.r.3"].text == "probable"
    assert "Not an HL7 ICSR message" in root.find(f"{{{NAMESPACE}}}notice").text


def test_report_section_validator_flags_numbers_and_references_not_in_the_data():
    text, kept, warnings = parse_report_section(
        {"text": "VY-CASE-0001 and VY-CASE-0099 were serious; 7 cases in total.", "citations": ["VY-CASE-0001", "VY-CASE-0099"]},
        allowed_refs={"VY-CASE-0001"},
        allowed_numbers={"0001", "3"},
    )
    assert kept == ["VY-CASE-0001"]
    assert any("Removed citations" in w for w in warnings)
    assert any("7" in w for w in warnings if w.startswith("Numbers"))
    assert any("VY-CASE-0099 is not part" in w for w in warnings)


def test_report_progress_and_markdown_mark_drafts():
    sections = [
        {"key": "a", "number": "A", "title": "Narrative", "status": "draft", "text": "Draft text.", "tables": []},
        {"key": "b", "number": "B", "title": "Actions", "status": "input_required", "text": "", "tables": []},
        {"key": "c", "number": "C", "title": "Index", "status": "generated", "text": "Index.",
         "tables": [{"title": "Cases", "columns": ["Case"], "rows": [["VY-CASE-0001"]]}]},
    ]
    assert progress(sections) == {"total": 3, "complete": 1, "draft": 1, "input_required": 1}
    markdown = to_markdown({
        "report": {"report_type": "pader", "report_number": "VY-PADER-0001", "status": "draft"},
        "version": 1,
        "signoff": None,
        "content": {"product": {"code": "VY-201", "name": "VY-201 (FICTIONAL)"},
                    "interval": {"start": "2026-06-01", "data_lock_point": "2026-11-26"}, "sections": sections},
    })
    assert "Not signed off: DRAFT" in markdown
    assert "_Machine draft, not yet reviewed._" in markdown
    assert "_Input required._" in markdown
    assert "| VY-CASE-0001 |" in markdown
