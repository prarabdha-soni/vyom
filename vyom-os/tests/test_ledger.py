from contextlib import contextmanager

import pytest

from vyom_literature.ledger import (
    LedgerConflictError,
    append_sys1_decision,
    canonical_state_hash,
    record_state_and_source,
)


class MemoryConnection:
    def __init__(self):
        self.states = {}
        self.sources = {}
        self.decisions = []
        self.next_id = 1

    @contextmanager
    def transaction(self):
        yield

    @contextmanager
    def cursor(self):
        yield MemoryCursor(self)


class MemoryCursor:
    def __init__(self, connection):
        self.connection = connection
        self.row = None

    def execute(self, query, params):
        normalized = " ".join(query.lower().split())
        if normalized.startswith("insert into clinical_states"):
            domain, dedup_key, title, state_json, state_hash = params
            key = (domain, dedup_key)
            if key in self.connection.states:
                self.row = None
            else:
                state_id = self.connection.next_id
                self.connection.next_id += 1
                self.connection.states[key] = (state_id, state_hash, state_json)
                self.row = (state_id, state_hash, state_json)
        elif normalized.startswith("select id, state_sha256, normalized_state from clinical_states"):
            state = self.connection.states.get((params[0], params[1]))
            self.row = state
        elif normalized.startswith("insert into source_records"):
            source, source_uid, _, state_id, _ = params
            key = (source, source_uid)
            if key in self.connection.sources:
                self.row = None
            else:
                self.connection.sources[key] = state_id
                self.row = (len(self.connection.sources),)
        elif normalized.startswith("select state_id from source_records"):
            state_id = self.connection.sources.get((params[0], params[1]))
            self.row = (state_id,) if state_id is not None else None
        elif normalized.startswith("insert into sys1_decisions"):
            decision_hash = params[4]
            state_id = params[-2]
            state_row = next(
                (row for row in self.connection.states.values() if row[0] == state_id), None
            )
            if state_row is None or state_row[1] != decision_hash:
                self.row = None
            else:
                self.connection.decisions.append(params)
                self.row = (len(self.connection.decisions),)
        elif normalized.startswith("select id from sys1_decisions"):
            state_id, model_id, sampler_version, schema_version, policy_version, state_hash = params
            match = next(
                (
                    decision
                    for decision in self.connection.decisions
                    if decision[-2] == state_id
                    and decision[0] == model_id
                    and decision[1] == sampler_version
                    and decision[2] == schema_version
                    and decision[3] == policy_version
                    and decision[4] == state_hash
                ),
                None,
            )
            self.row = (self.connection.decisions.index(match) + 1,) if match else None
        else:
            raise AssertionError(f"Unexpected SQL in mock: {query}")

    def fetchone(self):
        return self.row


def test_state_and_source_inserts_are_idempotent():
    connection = MemoryConnection()
    kwargs = {
        "domain": "pv_literature",
        "dedup_key": "doi:10.1000/example",
        "title_or_header": "Example article",
        "normalized_state": {"title": "Example", "abstract": "Public text"},
        "source": "pubmed",
        "source_uid": "10001",
        "raw_payload": {"pmid": "10001"},
    }

    first = record_state_and_source(connection, **kwargs)
    second = record_state_and_source(connection, **kwargs)

    assert first.state_created is True
    assert first.source_created is True
    assert second.state_created is False
    assert second.source_created is False
    assert first.state_id == second.state_id
    assert len(connection.states) == len(connection.sources) == 1


def test_same_source_id_cannot_be_relinked_to_another_state():
    connection = MemoryConnection()
    base = {
        "domain": "pv_literature",
        "title_or_header": "Article",
        "source": "pubmed",
        "source_uid": "10001",
        "raw_payload": {},
    }
    record_state_and_source(
        connection,
        **base,
        dedup_key="doi:10.1000/one",
        normalized_state={"title": "One"},
    )

    with pytest.raises(LedgerConflictError, match="already linked"):
        record_state_and_source(
            connection,
            **base,
            dedup_key="doi:10.1000/two",
            normalized_state={"title": "Two"},
        )


def test_decision_appends_only_when_state_hash_matches():
    connection = MemoryConnection()
    state = {"abstract": "Public text"}
    state_hash = canonical_state_hash(state)
    stored = record_state_and_source(
        connection,
        domain="pv_literature",
        dedup_key="pmid:10001",
        title_or_header="Example",
        normalized_state=state,
        source="pubmed",
        source_uid="10001",
        raw_payload={"raw": "public"},
    )
    decision = {
        "model_id": "jev-latest-test",
        "sampler_version": "mock-1",
        "question_schema_version": 2,
        "threshold_policy_version": 4,
        "state_sha256": state_hash,
        "latency_ms": 20,
        "answers": {"has_adverse_event": {"probability": 0.9}},
        "p_valid_case": None,
        "p_serious_event": 0.1,
        "confidence_band": "YELLOW_REVIEW",
    }

    decision_id = append_sys1_decision(connection, state_id=stored.state_id, decision=decision)

    assert decision_id == 1
    assert connection.decisions[0][4] == state_hash


def test_decision_rejects_mismatched_state_hash():
    connection = MemoryConnection()
    stored = record_state_and_source(
        connection,
        domain="pv_icsr",
        dedup_key="admission:mock",
        title_or_header="Mock ICSR",
        normalized_state={"report": "mock"},
        source="partner_e2b",
        source_uid="mock-1",
        raw_payload={"report": "mock"},
    )
    decision = {
        "model_id": "local-test",
        "sampler_version": "mock-1",
        "question_schema_version": 2,
        "threshold_policy_version": 4,
        "state_sha256": "0" * 64,
        "latency_ms": 1,
        "answers": {},
        "confidence_band": "YELLOW_REVIEW",
    }

    with pytest.raises(LedgerConflictError, match="does not match"):
        append_sys1_decision(connection, state_id=stored.state_id, decision=decision)