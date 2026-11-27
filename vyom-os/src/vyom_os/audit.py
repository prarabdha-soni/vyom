"""Append-only audit trail (``audit_events``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vyom_os.db import Jsonb, fetch_all

ENTITY_KINDS = ("case", "literature", "report", "product", "tenant", "user")


@dataclass(frozen=True)
class Actor:
    """The person (or system job) performing an action."""

    user_id: str | None
    role: str
    email: str | None = None

    @classmethod
    def system(cls) -> Actor:
        return cls(user_id=None, role="system", email=None)


def record(
    connection: Any,
    *,
    entity_kind: str,
    entity_ref: str,
    event_type: str,
    actor: Actor,
    detail: dict[str, Any] | None = None,
) -> None:
    if entity_kind not in ENTITY_KINDS:
        raise ValueError("unknown audit entity kind")
    connection.execute(
        """
        insert into audit_events (entity_kind, entity_ref, event_type, actor_id, actor_role, detail)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (entity_kind, entity_ref, event_type, actor.user_id, actor.role, Jsonb(detail or {})),
    )


def history(connection: Any, *, entity_kind: str, entity_ref: str, limit: int = 200) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        select event.id, event.event_type, event.actor_role, member.email as actor_email,
               event.detail, event.created_at
        from audit_events event
        left join tenant_members member on member.id = event.actor_id
        where event.entity_kind = %s and event.entity_ref = %s
        order by event.created_at desc, event.id desc
        limit %s
        """,
        (entity_kind, entity_ref, limit),
    )


def recent(connection: Any, *, limit: int = 12) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        select event.entity_kind, event.entity_ref, event.event_type, event.actor_role,
               member.email as actor_email, event.created_at
        from audit_events event
        left join tenant_members member on member.id = event.actor_id
        order by event.created_at desc, event.id desc
        limit %s
        """,
        (limit,),
    )
