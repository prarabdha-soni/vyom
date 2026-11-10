"""Per-record cost telemetry (A0, non-negotiable rule 10).

Every model call records tenant, item, model id, tokens/pages *when the
provider actually returned them*, and an estimated cost. Values the provider
does not expose are stored as NULL and reported as ``unavailable`` — they are
never fabricated.

Aggregation is deterministic SQL over the append-only ``model_cost_events``
table, bucketed per tenant / week / screened record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

#: Placeholder prices until finance confirms contracted rates. Every derived
#: number that uses these must be labelled "test-run estimate" in reports.
DEFAULT_PRICE_PER_1K_INPUT_TOKENS = Decimal("0.0005")
DEFAULT_PRICE_PER_1K_OUTPUT_TOKENS = Decimal("0.0015")
DEFAULT_PRICE_PER_OCR_PAGE = Decimal("0.02")

UNAVAILABLE = None


@dataclass(frozen=True)
class CostEvent:
    tenant_id: str
    item_type: str          # pv_literature | pv_icsr
    item_ref: str           # state id / decision id — never patient content
    provider: str           # vertex_ai | typesafe | local_ollama | anthropic
    model_id: str
    call_kind: str          # system_one | system_two | ocr_page
    input_tokens: int | None
    output_tokens: int | None
    pages: int | None
    unit_price_in: Decimal | None
    unit_price_out: Decimal | None
    estimated_cost_usd: Decimal | None
    latency_ms: int | None
    outcome: str            # ok | timeout | provider_error | malformed | fail_closed
    correlation_id: str
    prompt_version: str
    schema_version: str
    occurred_at: datetime


def estimate_cost(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    pages: int | None = None,
    price_in_per_1k: Decimal | None = DEFAULT_PRICE_PER_1K_INPUT_TOKENS,
    price_out_per_1k: Decimal | None = DEFAULT_PRICE_PER_1K_OUTPUT_TOKENS,
    price_per_page: Decimal | None = DEFAULT_PRICE_PER_OCR_PAGE,
) -> tuple[Decimal | None, bool]:
    """Return (estimated cost USD, whether any usage was known).

    If the provider gave no token counts and no page count we return
    (None, False): the value stays unavailable rather than invented.
    """
    total = Decimal("0")
    known = False
    if input_tokens is not None and price_in_per_1k is not None:
        total += Decimal(input_tokens) / Decimal(1000) * price_in_per_1k
        known = True
    if output_tokens is not None and price_out_per_1k is not None:
        total += Decimal(output_tokens) / Decimal(1000) * price_out_per_1k
        known = True
    if pages is not None and price_per_page is not None:
        total += Decimal(pages) * price_per_page
        known = True
    if not known:
        return None, False
    return total.quantize(Decimal("0.000001")), True


def build_cost_event(
    *,
    tenant_id: str,
    item_type: str,
    item_ref: str,
    provider: str,
    model_id: str,
    call_kind: str,
    correlation_id: str,
    prompt_version: str,
    schema_version: str,
    outcome: str,
    usage: dict[str, Any] | None = None,
    latency_ms: int | None = None,
    pages: int | None = None,
    occurred_at: datetime | None = None,
) -> CostEvent:
    usage = usage or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    estimated, _known = estimate_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pages=pages,
    )
    return CostEvent(
        tenant_id=tenant_id,
        item_type=item_type,
        item_ref=item_ref,
        provider=provider,
        model_id=model_id,
        call_kind=call_kind,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pages=pages,
        unit_price_in=DEFAULT_PRICE_PER_1K_INPUT_TOKENS,
        unit_price_out=DEFAULT_PRICE_PER_1K_OUTPUT_TOKENS,
        estimated_cost_usd=estimated,
        latency_ms=latency_ms,
        outcome=outcome,
        correlation_id=correlation_id,
        prompt_version=prompt_version,
        schema_version=schema_version,
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )


def record_cost_event(connection: Any, event: CostEvent) -> int:
    """Append one immutable cost event; returns its id."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into model_cost_events (
                  tenant_id, item_type, item_ref, provider, model_id, call_kind,
                  input_tokens, output_tokens, pages,
                  unit_price_in_per_1k, unit_price_out_per_1k, estimated_cost_usd,
                  latency_ms, outcome, correlation_id, prompt_version,
                  schema_version, occurred_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    event.tenant_id,
                    event.item_type,
                    event.item_ref,
                    event.provider,
                    event.model_id,
                    event.call_kind,
                    event.input_tokens,
                    event.output_tokens,
                    event.pages,
                    event.unit_price_in,
                    event.unit_price_out,
                    event.estimated_cost_usd,
                    event.latency_ms,
                    event.outcome,
                    event.correlation_id,
                    event.prompt_version,
                    event.schema_version,
                    event.occurred_at,
                ),
            )
            return int(cursor.fetchone()[0])


def weekly_cost_rollup(connection: Any, *, tenant_id: str, week_start: date) -> dict[str, Any]:
    """Cost per screened record for one tenant-week (A0 acceptance)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              count(*) filter (where estimated_cost_usd is null),
              coalesce(sum(estimated_cost_usd), 0),
              count(distinct item_ref),
              count(*)
            from model_cost_events
            where tenant_id = %s and occurred_at >= %s and occurred_at < %s + interval '7 days'
            """,
            (tenant_id, week_start, week_start),
        )
        unavailable_calls, total_raw, records, calls = cursor.fetchone()
    total = Decimal(str(total_raw))
    records = int(records)
    return {
        "tenant_id": tenant_id,
        "week_start": week_start.isoformat(),
        "calls": int(calls),
        "calls_with_unavailable_cost": int(unavailable_calls),
        "screened_records": records,
        "total_estimated_cost_usd": float(total),
        "cost_per_screened_record_usd": (float(total / records) if records else UNAVAILABLE),
        "note": "Test-run estimate at placeholder list prices; unavailable provider usage kept NULL.",
    }
