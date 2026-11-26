"""Tenant settings used by the request path.

``tenants`` is readable only by the service role, so the API resolves the
tenant once per request on the service connection and passes this immutable
context to the domain services, which run on the RLS-bound connection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vyom_os.db import fetch_one


@dataclass(frozen=True)
class TenantContext:
    id: str
    slug: str
    display_name: str
    kind: str = "mah"
    is_fictional: bool = False
    residency_region: str = "asia-south1"
    hosted_processing_allowed: bool = False
    meddra_licence_state: str = "none"
    meddra_dictionary: str | None = None
    clock_policy: dict[str, Any] = field(default_factory=dict)
    auto_close_policy: dict[str, Any] = field(default_factory=dict)

    @property
    def licensed(self) -> bool:
        return self.meddra_licence_state == "licensed" and bool(self.meddra_dictionary)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "display_name": self.display_name,
            "kind": self.kind,
            "is_fictional": self.is_fictional,
            "residency_region": self.residency_region,
            "hosted_processing_allowed": self.hosted_processing_allowed,
            "meddra": {"licence_state": self.meddra_licence_state, "dictionary": self.meddra_dictionary},
            "clock_policy": self.clock_policy,
            "auto_close_enabled": any(bool(value) for value in self.auto_close_policy.values()),
        }


_COLUMNS = """
    id::text as id, slug, display_name, kind, is_fictional, residency_region,
    hosted_processing_allowed, meddra_licence_state, feature_flags, clock_policy, auto_close_policy
"""


def _context(row: dict[str, Any] | None) -> TenantContext | None:
    if row is None:
        return None
    flags = row.get("feature_flags") or {}
    return TenantContext(
        id=row["id"],
        slug=row["slug"],
        display_name=row["display_name"],
        kind=row["kind"],
        is_fictional=bool(row["is_fictional"]),
        residency_region=row["residency_region"],
        hosted_processing_allowed=bool(row["hosted_processing_allowed"]),
        meddra_licence_state=row["meddra_licence_state"],
        meddra_dictionary=flags.get("meddra_dictionary") if isinstance(flags, dict) else None,
        clock_policy=dict(row.get("clock_policy") or {}),
        auto_close_policy=dict(row.get("auto_close_policy") or {}),
    )


def load_tenant(service_connection: Any, tenant_id: str) -> TenantContext | None:
    return _context(fetch_one(service_connection, f"select {_COLUMNS} from tenants where id = %s", (tenant_id,)))


def load_tenant_by_slug(service_connection: Any, slug: str) -> TenantContext | None:
    return _context(fetch_one(service_connection, f"select {_COLUMNS} from tenants where slug = %s", (slug,)))
