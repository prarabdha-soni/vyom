from datetime import date

from vyom_os import rules
from vyom_os.models import CasePayload, CaseProduct, Coding, Patient, Reaction, Reporter


def _case(**overrides):
    base = {
        "patient": Patient(age_value=62, age_unit="years", sex="male", initials="R.K."),
        "reporter": Reporter(qualification="physician", identifiable=True, country="India"),
        "products": [CaseProduct(name="VY-201", product_code="VY-201", role="suspect")],
        "reactions": [Reaction(verbatim="angioedema of the lips", onset_date="2026-11-20", serious_criteria=["hospitalisation"])],
    }
    base.update(overrides)
    return CasePayload(**base)


def test_validity_needs_all_four_criteria():
    assert rules.validity(_case())["valid"] is True
    missing = rules.validity(_case(reactions=[], reporter=Reporter()))
    assert missing["valid"] is False
    assert missing["missing"] == ["identifiable_reporter", "adverse_event"]


def test_fatal_outcome_adds_death_criterion():
    case = _case(reactions=[Reaction(verbatim="Stevens-Johnson syndrome", outcome="fatal")])
    assert rules.seriousness(case) == {"serious": True, "criteria": ["death"]}


def test_expectedness_against_reference_terms():
    case = _case(reactions=[Reaction(verbatim="headache"), Reaction(verbatim="angioedema")])
    result = rules.expectedness(case, [{"term": "headache"}, {"term": "dizziness"}])
    assert [item["expected"] for item in result] == [True, False]
    assert result[0]["basis"] == "text match — confirm"
    assert rules.expectedness(case, None)[0]["expected"] is None


def test_confirmed_coding_is_the_basis_when_coded():
    reaction = Reaction(verbatim="swelling of lips", coding=Coding(pt="Angioedema", status="confirmed"))
    result = rules.expectedness(_case(reactions=[reaction]), [{"term": "Angioedema"}])
    assert result[0] == {"index": 0, "expected": True, "basis": "coded term"}


def test_serious_unexpected_is_an_expedited_candidate():
    assessed = rules.assess(
        _case(), reference_terms=[{"term": "headache"}], day_zero=date(2026, 11, 22),
        clock_policy=None, today=date(2026, 11, 26),
    )
    assert assessed["expedited_candidate"] is True
    assert assessed["clock"]["label"] == "Day 4 of 15"
    assert assessed["clock"]["due_date"] == "2026-12-07"


def test_clock_statuses():
    policy = {"serious_days": 15, "non_serious_days": 90}
    assert rules.clock(date(2026, 11, 1), True, policy, date(2026, 11, 14))["status"] == "due_soon"
    assert rules.clock(date(2026, 11, 1), True, policy, date(2026, 11, 20))["status"] == "overdue"
    assert rules.clock(date(2026, 11, 1), False, policy, date(2026, 11, 20))["status"] == "on_track"
    stopped = rules.clock(date(2026, 1, 1), True, policy, date(2026, 11, 20), closed=True)
    assert stopped["status"] == "stopped" and stopped["label"] == "Stopped"


def test_duplicate_score_finds_the_same_patient_and_event():
    first = _case()
    second = _case(reactions=[Reaction(verbatim="severe angioedema of the lips", onset_date="2026-11-20")])
    score, reasons = rules.duplicate_score(second, first)
    assert score >= rules.DUPLICATE_THRESHOLD
    assert "same reported event" in reasons
    other_product = _case(products=[CaseProduct(name="VY-305", product_code="VY-305")])
    assert rules.duplicate_score(other_product, first) == (0.0, [])
