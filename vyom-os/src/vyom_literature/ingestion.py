from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Protocol

from vyom_literature.cost import build_cost_event, record_cost_event
from vyom_literature.dedup import make_dedup_key
from vyom_literature.ledger import (
    append_sys1_decision,
    append_sys2_synthesis,
    has_sys1_decision,
    record_state_and_source,
)
from vyom_literature.observability import emit_event, new_correlation_id, timed_stage
from vyom_literature.records import LiteratureRecord

#: A1 bootstrap tenant — pre-tenant rows were backfilled to this id in
#: migration 004; the sweep defaults here until per-tenant scheduling lands.
BOOTSTRAP_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class LiteratureRouter(Protocol):
    def evaluate(self, domain: str, normalized_state: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SweepStats:
    fetched: int = 0
    invalid: int = 0
    states_created: int = 0
    sources_created: int = 0
    decisions_created: int = 0
    decisions_already_present: int = 0
    syntheses_created: int = 0
    fail_closed_count: int = 0


def _first_author(authors: list[dict[str, str]]) -> str | None:
    if not authors:
        return None
    return authors[0].get("surname") or authors[0].get("name")


def _publication_date(record: LiteratureRecord) -> date | None:
    if record.pub_date:
        return record.pub_date
    if record.publication_year:
        return date(record.publication_year, 1, 1)
    return None


def _record_cost(
    connection: Any,
    *,
    tenant_id: str,
    item_ref: str,
    provider_name: str,
    call_kind: str,
    decision_or_result: dict[str, Any] | None,
    model_id: str,
    correlation_id: str,
    schema_version: str,
    outcome: str,
    latency_ms: int | None,
) -> None:
    """Append one cost event per model call (A0 rule 10).

    Token usage comes only from what the provider actually returned; when it
    did not, the values stay NULL and are reported as unavailable.
    """
    usage = (decision_or_result or {}).get("usage")
    try:
        record_cost_event(
            connection,
            build_cost_event(
                tenant_id=tenant_id,
                item_type="pv_literature",
                item_ref=item_ref,
                provider=provider_name,
                model_id=(decision_or_result or {}).get("model_id", model_id),
                call_kind=call_kind,
                correlation_id=correlation_id,
                prompt_version=schema_version,
                schema_version=schema_version,
                outcome=outcome,
                usage=usage if isinstance(usage, dict) else None,
                latency_ms=latency_ms,
            ),
        )
    except Exception:  # noqa: BLE001 - cost telemetry must never break screening
        emit_event(
            "cost_telemetry_failed",
            correlation_id=correlation_id,
            call_kind=call_kind,
            level=40,
        )


def screen_public_records(
    records: Iterable[LiteratureRecord],
    *,
    connection: Any,
    router: LiteratureRouter,
    strategy_id: int | None = None,
    system_two_router: Any | None = None,
    tenant_id: str = BOOTSTRAP_TENANT_ID,
    correlation_id: str | None = None,
) -> SweepStats:
    fetched = invalid = states_created = sources_created = decisions_created = already_present = syntheses_created = fail_closed = 0
    correlation_id = correlation_id or new_correlation_id()

    for record in records:
        fetched += 1
        if not record.source_uid or not record.title.strip():
            invalid += 1
            continue

        normalized_state = {
            "domain": "pv_literature",
            "pmid": record.pmid,
            "doi": record.doi,
            "title": record.title,
            "abstract": record.abstract or "",
            "journal": record.journal,
            "pub_date": record.pub_date.isoformat() if record.pub_date else None,
            "publication_year": record.publication_year,
            "authors": record.authors,
        }
        dedup_key = make_dedup_key(
            doi=record.doi,
            pmid=record.pmid,
            title=record.title,
            first_author=_first_author(record.authors),
            pub_date=_publication_date(record),
            publication_year=record.publication_year,
        )
        with timed_stage("ingest", correlation_id=correlation_id, strategy_id=strategy_id):
            state_write = record_state_and_source(
                connection,
                domain="pv_literature",
                dedup_key=dedup_key,
                title_or_header=record.title,
                normalized_state=normalized_state,
                source=record.source,
                source_uid=record.source_uid,
                raw_payload=record.raw,
                strategy_id=strategy_id,
            )
        states_created += int(state_write.state_created)
        sources_created += int(state_write.source_created)

        existing_decision = {
            "model_id": router.public_model,
            "sampler_version": router.sampler_version,
            "question_schema_version": router.question_schema_version,
            "threshold_policy_version": router.threshold_policy_version,
            "state_sha256": state_write.state_sha256,
        }
        if has_sys1_decision(connection, state_id=state_write.state_id, decision=existing_decision):
            already_present += 1
            # A0: same-day rerun is a no-op — no second model call, no ledger row.
            emit_event(
                "screening_skipped_idempotent",
                correlation_id=correlation_id,
                state_id=state_write.state_id,
                strategy_id=strategy_id,
            )
            continue

        decision = router.evaluate("pv_literature", state_write.normalized_state)
        if decision["state_sha256"] != state_write.state_sha256:
            raise ValueError("router evaluated a different state than the one stored in the ledger")
        outcome = decision.get("outcome", "ok")
        if outcome != "ok":
            # A0 fail-closed guarantee: a provider failure/malformed proposal
            # can never be GREEN_CLOSE / GREEN_PASS — it must route to a human.
            if decision.get("confidence_band") in {"GREEN_CLOSE", "GREEN_PASS"}:
                raise AssertionError(
                    "fail-closed violation: non-ok System One outcome produced a GREEN band"
                )
            fail_closed += 1
        emit_event(
            "system_one_decision",
            correlation_id=correlation_id,
            state_id=state_write.state_id,
            model_id=decision["model_id"],
            sampler_version=decision["sampler_version"],
            question_schema_version=decision["question_schema_version"],
            threshold_policy_version=decision["threshold_policy_version"],
            confidence_band=decision["confidence_band"],
            outcome=outcome,
            latency_ms=decision.get("latency_ms"),
        )
        _record_cost(
            connection,
            tenant_id=tenant_id,
            item_ref=str(state_write.state_id),
            provider_name=str(decision.get("provider", "unknown")),
            call_kind="system_one",
            decision_or_result=decision,
            model_id=decision["model_id"],
            correlation_id=correlation_id,
            schema_version=str(decision["question_schema_version"]),
            outcome=str(outcome),
            latency_ms=decision.get("latency_ms"),
        )
        decision_id = append_sys1_decision(connection, state_id=state_write.state_id, decision=decision)
        decisions_created += 1
        if system_two_router is not None:
            with timed_stage("system_two", correlation_id=correlation_id, state_id=state_write.state_id):
                try:
                    synthesis = system_two_router.synthesize(
                        domain="pv_literature",
                        state=state_write.normalized_state,
                        decision=decision,
                    )
                except Exception as error:  # noqa: BLE001 - System Two must never fail the sweep
                    emit_event(
                        "system_two_failed",
                        correlation_id=correlation_id,
                        state_id=state_write.state_id,
                        error_type=type(error).__name__,
                        level=40,
                    )
                    synthesis = None
            if synthesis is not None:
                append_sys2_synthesis(
                    connection,
                    decision_id=decision_id,
                    synthesis=synthesis,
                )
                syntheses_created += 1
                _record_cost(
                    connection,
                    tenant_id=tenant_id,
                    item_ref=str(state_write.state_id),
                    provider_name=str(getattr(system_two_router, "public_model", "unknown")),
                    call_kind="system_two",
                    decision_or_result=getattr(synthesis, "metadata", None) if isinstance(getattr(synthesis, "metadata", None), dict) else {},
                    model_id=synthesis.model_id,
                    correlation_id=correlation_id,
                    schema_version=str(decision["question_schema_version"]),
                    outcome="ok",
                    latency_ms=None,
                )
        emit_event(
            "queued_for_review",
            correlation_id=correlation_id,
            state_id=state_write.state_id,
            decision_id=decision_id,
            confidence_band=decision["confidence_band"],
        )

    return SweepStats(
        fetched=fetched,
        invalid=invalid,
        states_created=states_created,
        sources_created=sources_created,
        decisions_created=decisions_created,
        decisions_already_present=already_present,
        syntheses_created=syntheses_created,
        fail_closed_count=fail_closed,
    )