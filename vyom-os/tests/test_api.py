from contextlib import contextmanager
from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from vyom_literature.api import MAX_STATE_BYTES, ReviewerIdentity, create_app
from vyom_literature.ledger import StateWrite, canonical_state_hash


class FakeRouter:
    def __init__(self):
        self.calls = []

    def evaluate(self, domain, state):
        self.calls.append((domain, state))
        return {
            "model_id": "local-test-model",
            "sampler_version": "test-1",
            "question_schema_version": 2,
            "threshold_policy_version": 4,
            "state_sha256": canonical_state_hash(state),
            "latency_ms": 8,
            "answers": {"claim_submission_route": {"choice": "READY_FOR_HUMAN_RELEASE"}},
            "gate_probabilities": {"diagnostic_proof_attached": 0.98},
            "p_valid_case": None,
            "p_serious_or_denial": None,
            "confidence_band": "GREEN_PASS",
            "recommended_route": "READY_FOR_HUMAN_RELEASE",
        }


class FakeConnection:
    @contextmanager
    def __enter__(self):
        yield self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _client(monkeypatch, *, runner=None, hospital_rcm_enabled=False):
    router = FakeRouter()
    writes = {"states": 0, "decisions": 0}

    def fake_record_state(connection, **kwargs):
        writes["states"] += 1
        state = kwargs["normalized_state"]
        return StateWrite(
            state_id=41,
            state_created=writes["states"] == 1,
            source_created=writes["states"] == 1,
            state_sha256=canonical_state_hash(state),
            normalized_state=state,
        )


    saved_decisions = {}

    def fake_append_decision(connection, *, state_id, decision):
        # Like the real ledger: a repeat of the same decision is not saved again;
        # the number of the one already saved is returned instead.
        key = (state_id, decision["state_sha256"])
        if key not in saved_decisions:
            writes["decisions"] += 1
            saved_decisions[key] = 70 + writes["decisions"]
        return saved_decisions[key]

    monkeypatch.setattr("vyom_literature.api.record_state_and_source", fake_record_state)
    monkeypatch.setattr("vyom_literature.api.append_sys1_decision", fake_append_decision)
    app = create_app(
        router=router,
        connection_factory=FakeConnection,
        api_token="unit-test-token",
        reviewer_tokens={
            "review-token": ReviewerIdentity(
                id=UUID("12345678-1234-5678-1234-567812345678"),
                role="safety_physician",
            )
        },
        literature_runner=runner,
        hospital_rcm_enabled=hospital_rcm_enabled,
    )
    return TestClient(app), router, writes


def test_health_is_available_without_authentication(monkeypatch):
    client, _, _ = _client(monkeypatch)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rcm_route_requires_token_and_persists_ledger(monkeypatch):
    client, router, writes = _client(monkeypatch, hospital_rcm_enabled=True)
    body = {
        "admission_uid": "mock-admission-1",
        "payer_code": "mock-payer",
        "normalized_state": {"diagnosis": "mock", "treatment": ["mock"]},
    }

    denied = client.post("/v1/rcm/preflight", json=body)
    accepted = client.post(
        "/v1/rcm/preflight",
        json=body,
        headers={"Authorization": "Bearer unit-test-token"},
    )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["requires_human_release"] is True
    assert accepted.json()["recommended_route"] == "READY_FOR_HUMAN_RELEASE"
    assert writes == {"states": 1, "decisions": 1}
    assert router.calls[0][0] == "hospital_rcm"
    assert router.calls[0][1]["domain"] == "hospital_rcm"


def test_rcm_retry_returns_existing_decision_without_duplicate(monkeypatch):
    client, _, writes = _client(monkeypatch, hospital_rcm_enabled=True)
    body = {
        "admission_uid": "mock-admission-2",
        "payer_code": "mock-payer",
        "normalized_state": {"diagnosis": "mock"},
    }
    headers = {"Authorization": "Bearer unit-test-token"}

    first = client.post("/v1/rcm/preflight", json=body, headers=headers)
    retry = client.post("/v1/rcm/preflight", json=body, headers=headers)

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["decision_id"] == first.json()["decision_id"]
    assert writes["decisions"] == 1


def test_rcm_rejects_oversized_normalized_state_before_model_call(monkeypatch):
    client, router, _ = _client(monkeypatch, hospital_rcm_enabled=True)
    body = {
        "admission_uid": "mock-admission-3",
        "payer_code": "mock-payer",
        "normalized_state": {"text": "x" * MAX_STATE_BYTES},
    }

    response = client.post(
        "/v1/rcm/preflight",
        json=body,
        headers={"Authorization": "Bearer unit-test-token"},
    )

    assert response.status_code == 413
    assert router.calls == []


def test_rcm_route_is_not_registered_by_default(monkeypatch):
    client, router, _ = _client(monkeypatch)
    response = client.post(
        "/v1/rcm/preflight",
        json={
            "admission_uid": "mock-admission-disabled",
            "payer_code": "mock-payer",
            "normalized_state": {},
        },
        headers={"Authorization": "Bearer unit-test-token"},
    )

    assert response.status_code == 404
    assert router.calls == []


def test_literature_sweep_checks_dates_and_returns_runner_result(monkeypatch):
    runner_calls = []

    def runner(from_date, to_date):
        runner_calls.append((from_date, to_date))
        return [{"strategy_id": 3, "decisions_created": 2}]

    client, _, _ = _client(monkeypatch, runner=runner)
    headers = {"Authorization": "Bearer unit-test-token"}
    invalid = client.post(
        "/v1/literature/sweep",
        json={"from_date": "2026-10-15", "to_date": "2026-10-14"},
        headers=headers,
    )
    valid = client.post(
        "/v1/literature/sweep",
        json={"from_date": "2026-10-13", "to_date": "2026-10-14"},
        headers=headers,
    )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    assert valid.json() == {"strategies": [{"strategy_id": 3, "decisions_created": 2}]}
    assert runner_calls == [(date(2026, 10, 13), date(2026, 10, 14))]


def test_unconfigured_literature_sweep_is_not_silently_accepted(monkeypatch):
    client, _, _ = _client(monkeypatch)
    response = client.post(
        "/v1/literature/sweep",
        json={"from_date": "2026-10-13", "to_date": "2026-10-14"},
        headers={"Authorization": "Bearer unit-test-token"},
    )

    assert response.status_code == 503


def test_review_queue_requires_reviewer_token_and_returns_queue(monkeypatch):
    seen = []

    def queue(connection, *, domain, limit):
        seen.append((domain, limit))
        return [{"state_id": 8, "confidence_band": "RED_ESCALATE"}]

    monkeypatch.setattr("vyom_literature.api.fetch_review_queue", queue)
    client, _, _ = _client(monkeypatch)

    denied = client.get("/v1/review/queue", headers={"Authorization": "Bearer unit-test-token"})
    accepted = client.get(
        "/v1/review/queue?domain=pv_literature&limit=20",
        headers={"Authorization": "Bearer review-token"},
    )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json() == {"items": [{"state_id": 8, "confidence_band": "RED_ESCALATE"}]}
    assert seen == [("pv_literature", 20)]


def test_review_action_uses_server_mapped_reviewer_identity(monkeypatch):
    seen = []

    def append_label(connection, **kwargs):
        seen.append(kwargs)
        return 101

    monkeypatch.setattr("vyom_literature.api.append_review_label", append_label)
    client, _, _ = _client(monkeypatch)
    response = client.post(
        "/v1/review/states/8/actions",
        json={"decision_id": 12, "action": "CORRECT", "override_patch": {"has_adverse_event": False}},
        headers={"Authorization": "Bearer review-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"label_id": 101, "split": "pool", "action": "CORRECT"}
    assert seen[0]["reviewer_id"] == UUID("12345678-1234-5678-1234-567812345678")
    assert seen[0]["reviewer_role"] == "safety_physician"


def test_gold_report_uses_only_versioned_gold_rows(monkeypatch):
    calls = []

    def gold_rows(connection, **kwargs):
        calls.append(kwargs)
        return [
            {"state_id": 1, "title_or_header": "miss", "model_id": "m", "confidence_band": "GREEN_CLOSE", "is_valid_case": True},
            {"state_id": 2, "title_or_header": "hit", "model_id": "m", "confidence_band": "RED_ESCALATE", "is_valid_case": True},
        ]

    monkeypatch.setattr("vyom_literature.api.fetch_gold_decisions", gold_rows)
    client, _, _ = _client(monkeypatch)
    response = client.get(
        "/v1/reports/gold/gold-v1?model_id=m&sampler_version=s1&question_schema_version=2&threshold_policy_version=4",
        headers={"Authorization": "Bearer review-token"},
    )

    assert response.status_code == 200
    report = response.json()
    assert report["gold_set_version"] == "gold-v1"
    assert report["tp"] == 1 and report["fn"] == 1
    assert report["recall"] == 0.5
    assert report["misses"][0]["state_id"] == 1
    assert calls[0]["gold_set_version"] == "gold-v1"


def test_screening_log_is_version_grouped(monkeypatch):
    monkeypatch.setattr(
        "vyom_literature.api.fetch_screening_log",
        lambda connection, *, days: [{"domain": "pv_literature", "states_screened": 18}],
    )
    client, _, _ = _client(monkeypatch)
    response = client.get(
        "/v1/reports/screening-log?days=14",
        headers={"Authorization": "Bearer review-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"days": 14, "groups": [{"domain": "pv_literature", "states_screened": 18}]}