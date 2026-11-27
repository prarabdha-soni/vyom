"""``vyom-migrate``: apply the schema migrations in order, each exactly once.

Migrations are the files ``migrations/NNN_name.sql`` numbered 002 and up
(001 belongs to the retired v1 prototype and is never applied). Each file
runs in one transaction together with its row in ``schema_migrations``, which
records the file's SHA-256: a failed file leaves nothing behind, and a file
is never applied twice. A file that changed after it was applied stops the
run; write a new migration instead.

Run it with an owner or administrator connection, never the application's::

    MIGRATION_DATABASE_URL=... vyom-migrate             # apply what is pending
    MIGRATION_DATABASE_URL=... vyom-migrate --status    # report only
    MIGRATION_DATABASE_URL=... vyom-migrate --baseline  # record files as applied
                                                        # without running them

``--baseline`` is for a database that was migrated by hand before this tool
existed. After migrating, the login passwords of ``vyom_app`` and
``vyom_service`` are set from ``VYOM_APP_DB_PASSWORD`` and
``VYOM_SERVICE_DB_PASSWORD`` when those are present. Passwords are hashed
(SCRAM-SHA-256) on this side, so only the verifier reaches the server and
its logs.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import psycopg
from psycopg import sql

FIRST_NUMBER = 2
LOCK_KEY = 0x76796F6D  # "vyom": one migrator at a time across every replica and job
FILE_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
OUTER_BEGIN = re.compile(r"^\s*begin\s*;\s*$", re.IGNORECASE | re.MULTILINE)
OUTER_COMMIT = re.compile(r"^\s*commit\s*;\s*$", re.IGNORECASE | re.MULTILINE)
ROLE_PASSWORDS = (("vyom_app", "VYOM_APP_DB_PASSWORD"), ("vyom_service", "VYOM_SERVICE_DB_PASSWORD"))
MIN_ROLE_PASSWORD = 24

LEDGER = """
create table if not exists schema_migrations (
  name        text primary key,
  checksum    text not null check (checksum ~ '^[0-9a-f]{64}$'),
  baseline    boolean not null default false,
  applied_by  text not null default current_user,
  applied_at  timestamptz not null default now()
)
"""


class MigrationError(Exception):
    """The migrations on disk and in the database disagree; nothing was changed."""


@dataclass(frozen=True)
class Migration:
    number: int
    name: str
    text: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def body(self) -> str:
        """The statements to run. A file's own outer ``begin;``/``commit;`` is dropped: the runner owns the transaction."""
        begins, commits = list(OUTER_BEGIN.finditer(self.text)), list(OUTER_COMMIT.finditer(self.text))
        if not begins and not commits:
            return self.text
        wrapped = (
            len(begins) == 1
            and len(commits) == 1
            and _only_comments(self.text[: begins[0].start()])
            and _only_comments(self.text[commits[0].end() :])
        )
        if not wrapped:
            raise MigrationError(f"{self.name}: begin; and commit; may only wrap the whole file, once")
        return self.text[begins[0].end() : commits[0].start()]


def _only_comments(text: str) -> bool:
    return all(line.strip() == "" or line.strip().startswith("--") for line in text.splitlines())


def default_directory() -> Path:
    configured = os.environ.get("VYOM_MIGRATIONS_DIR", "").strip()
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "migrations"


def discover(directory: Path) -> list[Migration]:
    if not directory.is_dir():
        raise MigrationError(f"No migrations directory at {directory}. Set VYOM_MIGRATIONS_DIR.")
    found = []
    for path in sorted(directory.iterdir()):
        match = FILE_NAME.match(path.name)
        if match and int(match.group(1)) >= FIRST_NUMBER:
            found.append(Migration(int(match.group(1)), path.name, path.read_text(encoding="utf-8")))
    numbers = [migration.number for migration in found]
    if len(numbers) != len(set(numbers)):
        raise MigrationError("Two migration files share a number.")
    if not found:
        raise MigrationError(f"No migrations found in {directory}.")
    return found


def plan(migrations: list[Migration], applied: dict[str, str]) -> list[Migration]:
    """The migrations still to apply, in order, after checking history has not diverged."""
    on_disk = {migration.name for migration in migrations}
    missing = sorted(set(applied) - on_disk)
    if missing:
        raise MigrationError(
            f"The database has migrations this build does not: {', '.join(missing)}. Deploy a build that includes them."
        )
    changed = [m.name for m in migrations if m.name in applied and applied[m.name] != m.checksum]
    if changed:
        raise MigrationError(
            f"Changed after being applied: {', '.join(changed)}. Restore the file and write a new migration instead."
        )
    pending = [m for m in migrations if m.name not in applied]
    if pending and applied:
        latest = max(m.number for m in migrations if m.name in applied)
        early = [m.name for m in pending if m.number < latest]
        if early:
            raise MigrationError(f"Numbered before migrations already applied: {', '.join(early)}. Renumber them.")
    return pending


def run(url: str, directory: Path, *, baseline: bool = False, status: bool = False, out: TextIO = sys.stdout) -> list[str]:
    """Apply (or with ``baseline``, record) pending migrations. Returns the names handled."""
    migrations = discover(directory)
    handled: list[str] = []
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute("select pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
            connection.execute(LEDGER)
            applied = dict(connection.execute("select name, checksum from schema_migrations").fetchall())
            pending = plan(migrations, applied)
            if status:
                for migration in migrations:
                    out.write(f"{'applied ' if migration.name in applied else 'pending '} {migration.name}\n")
                return [m.name for m in pending]
            for migration in pending:
                body = migration.body()
                with connection.transaction():
                    if not baseline:
                        connection.execute(body)  # type: ignore[arg-type]  # trusted file from this repository
                    connection.execute(
                        "insert into schema_migrations (name, checksum, baseline) values (%s, %s, %s)",
                        (migration.name, migration.checksum, baseline),
                    )
                handled.append(migration.name)
                out.write(f"{'recorded' if baseline else 'applied '} {migration.name}\n")
            if not pending:
                out.write("schema is up to date\n")
            _set_role_passwords(connection, out)
        finally:
            connection.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
    return handled


def _set_role_passwords(connection: psycopg.Connection, out: TextIO) -> None:
    for role, variable in ROLE_PASSWORDS:
        password = os.environ.get(variable, "")
        if not password:
            continue
        if len(password) < MIN_ROLE_PASSWORD:
            raise MigrationError(f"{variable} must be at least {MIN_ROLE_PASSWORD} characters.")
        verifier = connection.pgconn.encrypt_password(password.encode("utf-8"), role.encode("utf-8"), b"scram-sha-256")
        connection.execute(
            sql.SQL("alter role {} with login password {}").format(sql.Identifier(role), sql.Literal(verifier.decode("ascii")))
        )
        out.write(f"set login password for {role}\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="vyom-migrate", description="Apply Vyom OS schema migrations in order, each exactly once."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="List applied and pending migrations; change nothing.")
    mode.add_argument("--baseline", action="store_true", help="Record pending migrations as applied without running them.")
    parser.add_argument(
        "--dir", type=Path, default=None, help="Migrations directory (default: VYOM_MIGRATIONS_DIR or ./migrations)."
    )
    args = parser.parse_args(argv)

    url = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    if not url:
        parser.error("set MIGRATION_DATABASE_URL to an owner or administrator connection (not the application's)")
    try:
        pending = run(url, args.dir or default_directory(), baseline=args.baseline, status=args.status)
    except MigrationError as error:
        sys.stderr.write(f"vyom-migrate: {error}\n")
        sys.exit(2)
    if args.status and pending:
        sys.exit(1)  # pending work: useful as a deploy gate


if __name__ == "__main__":
    main()
