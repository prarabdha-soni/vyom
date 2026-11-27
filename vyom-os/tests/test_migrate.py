"""The migration runner's planning rules, without a database."""

from __future__ import annotations

from pathlib import Path

import pytest

from vyom_os.migrate import Migration, MigrationError, discover, plan

DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"


def test_discovers_numbered_files_from_002_in_order():
    migrations = discover(DIRECTORY)
    assert migrations[0].name.startswith("002_")
    assert [m.number for m in migrations] == sorted(m.number for m in migrations)
    assert all(not m.name.startswith("001_") for m in migrations)


def test_outer_transaction_is_left_to_the_runner():
    wrapped = next(m for m in discover(DIRECTORY) if m.name.startswith("004_"))
    body = wrapped.body()
    assert "create role vyom_app" in body
    assert all(line.strip().lower() not in ("begin;", "commit;") for line in body.splitlines())
    plain = Migration(3, "003_x.sql", "create table t (id int);\n")
    assert plain.body() == plain.text


def test_a_partial_transaction_is_refused():
    with pytest.raises(MigrationError):
        Migration(5, "005_x.sql", "create table a (id int);\nbegin;\ncreate table b (id int);\ncommit;\n").body()


def test_plan_returns_pending_and_guards_history():
    a, b, c = (Migration(n, f"00{n}_m.sql", f"select {n};") for n in (2, 3, 4))
    assert plan([a, b, c], {}) == [a, b, c]
    assert plan([a, b, c], {a.name: a.checksum}) == [b, c]
    with pytest.raises(MigrationError, match="Changed after being applied"):
        plan([a, b], {a.name: "0" * 64})
    with pytest.raises(MigrationError, match="does not"):
        plan([a], {a.name: a.checksum, b.name: b.checksum})
    with pytest.raises(MigrationError, match="Numbered before"):
        plan([a, b, c], {a.name: a.checksum, c.name: c.checksum})
