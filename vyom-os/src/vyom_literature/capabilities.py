from __future__ import annotations

from typing import Any


LITERATURE_CAPABILITY = "literature-screening"
LITERATURE_CAPABILITY_VERSION = 1
USAGE_UNITS = {"article_screened", "molecule_month", "case_completed"}


def record_usage_event(
    connection: Any,
    *,
    tenant_id: str,
    unit: str,
    source_ref: str,
    quantity: int = 1,
    capability_name: str = LITERATURE_CAPABILITY,
    capability_version: int = LITERATURE_CAPABILITY_VERSION,
) -> bool:
    if unit not in USAGE_UNITS:
        raise ValueError("unsupported usage unit")
    if quantity <= 0 or not source_ref:
        raise ValueError("usage quantity and source_ref must be positive and non-empty")

    with connection.cursor() as cursor:
        cursor.execute(
            "select id from capabilities where name = %s and version = %s",
            (capability_name, capability_version),
        )
        capability = cursor.fetchone()
        if capability is None:
            raise RuntimeError("usage capability is not registered")
        cursor.execute(
            """
            insert into usage_events (tenant_id, capability_id, unit, quantity, source_ref)
            values (%s, %s, %s, %s, %s)
            on conflict (tenant_id, capability_id, unit, source_ref) do nothing
            returning id
            """,
            (str(tenant_id), capability[0], unit, quantity, source_ref),
        )
        return cursor.fetchone() is not None