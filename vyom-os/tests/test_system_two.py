import pytest

from vyom_literature.system_two import SystemTwoRouter, validate_base_url


class FakeSynthesisProvider:
    def __init__(self, model_id, response):
        self.model_id = model_id
        self.response = response
        self.calls = []

    def draft(self, *, domain, state, decision):
        self.calls.append((domain, state, decision))
        return self.response


def _router(public_response=None, local_response=None):
    return SystemTwoRouter(
        public_literature_provider=FakeSynthesisProvider(
            "cloud-test", public_response or {"draft_narrative": "Review this case.", "cited_passages": [{"quote": "patient developed rash"}]}
        ),
        local_provider=FakeSynthesisProvider(
            "local-test", local_response or {"draft_narrative": "Review this chart.", "cited_passages": [{"quote": "IV therapy started"}]}
        ),
    )


def test_green_decisions_do_not_invoke_system_two():
    router = _router()
    result = router.synthesize(
        domain="pv_literature",
        state={"abstract": "patient developed rash"},
        decision={"confidence_band": "GREEN_CLOSE", "answers": {}},
    )

    assert result is None
    assert router.public_literature_provider.calls == []


def test_public_literature_yellow_uses_cloud_and_validates_offsets():
    router = _router()
    state = {"abstract": "A patient developed rash after treatment."}
    result = router.synthesize(
        domain="pv_literature",
        state=state,
        decision={"confidence_band": "YELLOW_REVIEW", "answers": {}},
    )

    assert len(router.public_literature_provider.calls) == 1
    assert router.local_provider.calls == []
    assert result.model_id == "cloud-test"
    assert result.cited_passages == [{"quote": "patient developed rash", "start_char": 2, "end_char": 24}]


def test_identifiable_icsr_red_uses_local_provider():
    router = _router()
    result = router.synthesize(
        domain="pv_icsr",
        state={"clinical_note": "IV therapy started after admission."},
        decision={"confidence_band": "RED_ESCALATE", "answers": {}},
    )

    assert router.public_literature_provider.calls == []
    assert len(router.local_provider.calls) == 1
    assert result.model_id == "local-test"


def test_unverifiable_quote_fails_closed():
    router = _router(
        public_response={"draft_narrative": "Unsupported.", "cited_passages": [{"quote": "not in source"}]}
    )

    with pytest.raises(ValueError, match="exact source quotation"):
        router.synthesize(
            domain="pv_literature",
            state={"abstract": "public source text"},
            decision={"confidence_band": "RED_ESCALATE", "answers": {}},
        )


def test_local_synthesis_base_url_rejects_remote_host():
    with pytest.raises(ValueError, match="approved local host"):
        validate_base_url("http://public-provider.example/v1")