from datetime import date
from types import SimpleNamespace

from vyom_literature.ingestion import screen_public_records
from vyom_literature.ledger import StateWrite, canonical_state_hash
from vyom_literature.records import LiteratureRecord


def _record(uid="10001", doi="10.1000/example"):
    return LiteratureRecord(
        source="pubmed",
        source_uid=uid,
        pmid=uid,
        doi=doi,
        title="Example report",
        abstract="A public abstract.",
        journal="Example Journal",
        pub_date=date(2026, 10, 1),
        publication_year=2026,
        authors=[{"surname": "Example", "initials": "A"}],
        raw={"xml": "<PubmedArticle />"},
    )


class FakeRouter:
    public_model = "jev-mock"
    sampler_version = "sampler-mock-1"
    question_schema_version = 2
    threshold_policy_version = 4

    def __init__(self):
        self.calls = []

    def evaluate(self, domain, normalized_state):
        self.calls.append((domain, normalized_state))
        return {
            "model_id": self.public_model,
            "sampler_version": self.sampler_version,
            "question_schema_version": self.question_schema_version,
            "threshold_policy_version": self.threshold_policy_version,
            "state_sha256": canonical_state_hash(normalized_state),
            "latency_ms": 12,
            "answers": {},
            "p_valid_case": None,
            "p_serious_event": 0.1,
            "confidence_band": "YELLOW_REVIEW",
        }


class FakeConnection:
    pass


def test_public_sweep_records_then_screens_once(monkeypatch):
    calls = {"state": 0, "has_decision": False, "decision": 0}

    def record_state(*args, **kwargs):
        calls["state"] += 1
        state = kwargs["normalized_state"]
        return StateWrite(
            state_id=7,
            state_created=calls["state"] == 1,
            source_created=calls["state"] == 1,
            state_sha256=canonical_state_hash(state),
                normalized_state=state,
        )

    def has_decision(*args, **kwargs):
        return calls["has_decision"]

    def append_decision(*args, **kwargs):
        calls["decision"] += 1
        calls["has_decision"] = True
        return 11

    monkeypatch.setattr("vyom_literature.ingestion.record_state_and_source", record_state)
    monkeypatch.setattr("vyom_literature.ingestion.has_sys1_decision", has_decision)
    monkeypatch.setattr("vyom_literature.ingestion.append_sys1_decision", append_decision)
    router = FakeRouter()

    first = screen_public_records([_record()], connection=FakeConnection(), router=router, strategy_id=3)
    second = screen_public_records([_record()], connection=FakeConnection(), router=router, strategy_id=3)

    assert first.decisions_created == 1
    assert first.states_created == first.sources_created == 1
    assert second.decisions_already_present == 1
    assert second.decisions_created == 0
    assert len(router.calls) == 1


def test_invalid_source_record_is_counted_without_screening(monkeypatch):
    record = _record(uid="", doi=None)
    router = FakeRouter()
    stats = screen_public_records([record], connection=FakeConnection(), router=router)

    assert stats.fetched == 1
    assert stats.invalid == 1
    assert router.calls == []