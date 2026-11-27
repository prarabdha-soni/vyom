"""PostgreSQL access with row-level security.

Two connection kinds:

* ``service()`` — the service role. Used only for sign-in, tenant lookup,
  seeding and scheduled jobs. It can bypass RLS, so request handlers never
  run tenant data queries on it.
* ``tenant(tenant_id)`` — the RLS-bound ``vyom_app`` role inside one
  transaction with ``app.tenant_id`` set. Every request-path data query runs
  here; a missing or wrong tenant returns no rows rather than another
  tenant's rows.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

__all__ = ["Database", "Jsonb", "fetch_all", "fetch_one", "fetch_value"]


class Database:
    def __init__(self, service_url: str, app_url: str):
        self.service_url = service_url
        self.app_url = app_url

    @contextmanager
    def service(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.service_url) as connection:
            yield connection

    @contextmanager
    def tenant(self, tenant_id: str) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.app_url) as connection:
            with connection.transaction():
                connection.execute("select set_config('app.tenant_id', %s, true)", (str(tenant_id),))
                yield connection


def fetch_all(connection: Any, query: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return list(cursor.fetchall())


def fetch_one(connection: Any, query: str, params: Sequence[Any] | dict[str, Any] = ()) -> dict[str, Any] | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def fetch_value(connection: Any, query: str, params: Sequence[Any] | dict[str, Any] = ()) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()
        return None if row is None else row[0]
