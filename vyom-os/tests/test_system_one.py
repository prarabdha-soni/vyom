from types import SimpleNamespace

import pytest

from vyom_literature.system_one import SystemOneRouter


def _pv_answers(*, patient=0.9, reporter=0.9, drug=0.9, event=0.9, serious=0.1, priority=2, design="CASE_REPORT_OR_SERIES"):
    return {
        "has_identifiable_patient": {"probability": patient},
        "has_identifiable_reporter": {"probability": reporter},
        "has_suspect_drug": {"probability": drug},
        "has_adverse_event": {"probability": event},
        "is_serious_event": {"probability": serious},
        "study_design": {"choice": design},
        "triage_priority": {"score": priority},
    }


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def system_one(self, *, state, questions, model):
        self.calls.append({"state": state, "questions": questions, "model": model})
        return self.response


def _router(public_client, local_client):
    return SystemOneRouter(
        public_literature_client=public_client,
        local_client=local_client,
        public_model="jev-latest-test",
        local_model="ollama/test-local",
        sampler_version="test-sampler-1",
    )


def test_public_literature_uses_cloud_and_records_lineage():
    cloud = FakeClient(_pv_answers())
    local = FakeClient(_pv_answers())
    router = _router(cloud, local)

    result = router.evaluate("pv_literature", {"abstract": "Public abstract"})

    assert len(cloud.calls) == 1
    assert local.calls == []
    assert result["model_id"] == "jev-latest-test"
    assert result["sampler_version"] == "test-sampler-1"
    assert len(result["state_sha256"]) == 64
    assert result["p_valid_case"] is None
    assert result["confidence_band"] == "YELLOW_REVIEW"


def test_identifiable_icsr_uses_local_client():
    cloud = FakeClient(_pv_answers())
    local = FakeClient(_pv_answers())
    result = _router(cloud, local).evaluate("pv_icsr", {"clinical_note": "mock PHI"})

    assert cloud.calls == []
    assert len(local.calls) == 1
    assert result["model_id"] == "ollama/test-local"


def test_only_all_low_validity_gates_and_negative_design_can_auto_close():
    answers = _pv_answers(
        patient=0.01,
        reporter=0.02,
        drug=0.01,
        event=0.03,
        design="IN_VITRO_OR_ANIMAL_ONLY",
    )
    result = _router(FakeClient(answers), FakeClient(_pv_answers())).evaluate(
        "pv_literature", {"abstract": "Cell study"}
    )

    assert result["confidence_band"] == "GREEN_CLOSE"


def test_one_high_validity_gate_prevents_auto_close():
    answers = _pv_answers(
        patient=0.01,
        reporter=0.02,
        drug=0.80,
        event=0.03,
        design="IN_VITRO_OR_ANIMAL_ONLY",
    )
    result = _router(FakeClient(answers), FakeClient(_pv_answers())).evaluate(
        "pv_literature", {"abstract": "Possible drug mention"}
    )

    assert result["confidence_band"] != "GREEN_CLOSE"


def test_high_risk_pv_escalates():
    result = _router(
        FakeClient(_pv_answers(serious=0.9, priority=5)), FakeClient(_pv_answers())
    ).evaluate("pv_literature", {"abstract": "Fatal case"})

    assert result["confidence_band"] == "RED_ESCALATE"


def test_invalid_probability_fails_closed_to_human_review():
    """A0: an out-of-contract probability is malformed output — it must route
    to a human (YELLOW_REVIEW) and can never become GREEN or auto-close."""
    answers = _pv_answers(patient=1.2)
    router = _router(FakeClient(answers), FakeClient(_pv_answers()))

    decision = router.evaluate("pv_literature", {"abstract": "Mock"})

    assert decision["confidence_band"] == "YELLOW_REVIEW"
    assert decision["outcome"] == "malformed_output"
    assert "between 0 and 1" in decision["fail_closed_reason"]


def test_unknown_domain_is_rejected_before_model_call():
    cloud = FakeClient(_pv_answers())
    router = _router(cloud, FakeClient(_pv_answers()))

    with pytest.raises(ValueError, match="Unsupported domain"):
        router.evaluate("unknown", {})
    assert cloud.calls == []