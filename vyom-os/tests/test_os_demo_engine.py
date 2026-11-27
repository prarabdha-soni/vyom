"""The deterministic demo engine against the fictional sample data."""

from datetime import date

import pytest

from vyom_literature.system_one import PV_LITERATURE_QUESTIONS, SystemOneRouter
from vyom_os import rules
from vyom_os.ai import demo
from vyom_os.ai.providers import DemoProvider
from vyom_os.ai.tasks import parse_extraction, parse_narrative
from vyom_os.literature import demo_records, fill_dates, load_fixture

TODAY = date(2026, 11, 26)
PRODUCTS = [{"code": code, "name": f"{code} (FICTIONAL)", "active_ingredient": None} for code in ("VY-201", "VY-305", "VY-412")]
REPORTS = {report["id"]: report for report in load_fixture("intake.json")["reports"]}


def _extract(report_id):
    report = REPORTS[report_id]
    text = fill_dates(report["text"], TODAY)
    output = demo.extract(text, {"channel": report["channel"], "tenant_products": PRODUCTS})
    return text, parse_extraction(output, source_text=text, tenant_products=PRODUCTS, channel=report["channel"])


def test_fill_dates_writes_days_before_today():
    assert fill_dates("on {d-6} and {d-0}", TODAY) == "on 20 November 2026 and 26 November 2026"


@pytest.mark.parametrize("report_id", sorted(REPORTS))
def test_every_evidence_quote_is_found_in_the_source(report_id):
    _text, result = _extract(report_id)
    assert all(item.status == "verified" for item in result.payload.evidence.values())


def test_serious_email_report():
    _text, result = _extract("E1")
    payload = result.payload
    assert payload.patient.initials == "R.K." and payload.patient.sex == "male" and payload.patient.age_value == 62
    assert payload.reporter.qualification == "physician" and payload.reporter.identifiable
    suspect = payload.products[0]
    assert (suspect.product_code, suspect.action_taken, suspect.start_date) == ("VY-201", "withdrawn", "2026-11-12")
    reaction = payload.reactions[0]
    assert reaction.verbatim == "severe angioedema of the lips and tongue"
    assert reaction.onset_date == "2026-11-20" and reaction.serious_criteria == ["hospitalisation"]
    assert payload.dechallenge == "positive"


def test_reporter_is_the_caller_not_the_doctor_mentioned():
    _text, result = _extract("H2")
    assert result.payload.reporter.qualification == "pharmacist"
    assert result.payload.reactions[0].onset_date == "2026-08-03"


def test_quality_complaint_is_not_a_valid_case():
    _text, result = _extract("E7")
    assert rules.validity(result.payload)["missing"] == ["identifiable_patient", "identifiable_reporter", "adverse_event"]


def test_pregnancy_and_concomitant_product():
    _text, result = _extract("E3")
    roles = {(p.product_code, p.role) for p in result.payload.products}
    assert roles == {("VY-201", "suspect"), ("VY-412", "concomitant")}
    assert {s.kind for s in result.payload.special_situations} == {"pregnancy"}


def test_follow_up_report_scores_as_duplicate():
    _t1, first = _extract("E1")
    _t2, second = _extract("E5")
    score, _reasons = rules.duplicate_score(second.payload, first.payload)
    assert score >= rules.DUPLICATE_THRESHOLD


def test_narrative_cites_only_source_text():
    text, result = _extract("E4")
    output = demo.narrative({
        "case_data": result.payload.model_dump(mode="json"),
        "evidence_quotes": [item.quote for item in result.payload.evidence.values()],
    })
    narrative, citations, warnings = parse_narrative(output, source_text=text)
    assert "pneumonia" in narrative and citations and not warnings
    assert "causal" not in narrative.casefold()


def test_literature_bands_follow_the_router():
    provider = DemoProvider()
    router = SystemOneRouter(
        public_literature_client=provider, local_client=provider, public_model=demo.DEMO_MODEL_ID,
        local_model=demo.DEMO_MODEL_ID, sampler_version=demo.DEMO_SAMPLER_VERSION,
    )
    bands = {}
    for record in demo_records(TODAY):
        state = {"title": record.title, "abstract": record.abstract, "authors": record.authors}
        bands[record.source_uid] = router.evaluate("pv_literature", state)["confidence_band"]
    assert {key for key, band in bands.items() if band == "GREEN_CLOSE"} == {"VY-LIT-0005", "VY-LIT-0006", "VY-LIT-0012"}
    assert bands["VY-LIT-0011"] == "RED_ESCALATE" and bands["VY-LIT-0008"] == "RED_ESCALATE"
    assert bands["VY-LIT-0004"] == "YELLOW_REVIEW"


def test_demo_system_one_answers_pass_the_contract():
    from vyom_literature.providers.vertex_ai import validate_system_one_output

    answers = demo.system_one({"title": "x", "abstract": "We report a 50-year-old man on VY-201 who had a rash."}, PV_LITERATURE_QUESTIONS)
    assert validate_system_one_output(answers, PV_LITERATURE_QUESTIONS)
