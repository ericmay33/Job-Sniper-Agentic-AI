"""Forward-only migration runner.

Migrations are numbered SQL files, applied in numeric order, recorded in
`schema_migrations`. There is no `down` step: rolling a schema backwards throws
away data, and this project's whole premise is that accumulated data is the asset.

Two properties are enforced rather than merely documented, because both fail
silently otherwise:

* **An applied migration is immutable.** Its checksum is stored, and a changed
  file is a hard error. Editing an applied migration means the database and the
  repo disagree about what the schema is, and nothing else would ever notice.
* **Versions only move forward.** A pending migration numbered below the highest
  applied one is rejected, so a file that arrives late (a rebase, a stale branch)
  cannot silently skip.

The module is split: `parse_filename`, `discover`, and `plan` are pure and hold
all the branching logic, so they are tested without a database. Only the
functions below the divider touch a connection.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from jobsniper.db.engine import default_migrations_dir

#: `NNN_some_name.sql`. The number is the version; the rest is a human label.
_FILENAME = re.compile(r"^(\d+)_([A-Za-z0-9][A-Za-z0-9_-]*)\.sql$")

#: Arbitrary but stable key for the run-wide advisory lock.
_LOCK_KEY = 8675309

_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    integer     PRIMARY KEY,
    name       text        NOT NULL,
    checksum   text        NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    """Base for everything this module refuses to do."""


class MalformedMigrationNameError(MigrationError):
    """A file in `migrations/` is not named `NNN_name.sql`."""


class DuplicateMigrationVersionError(MigrationError):
    """Two files claim the same version number."""


class MigrationDriftError(MigrationError):
    """The repo and the database disagree about what has been applied."""


@dataclass(frozen=True)
class Migration:
    """A migration file on disk."""

    version: int
    name: str
    path: Path
    sql: str
    checksum: str

    @property
    def label(self) -> str:
        return f"{self.version:03d}_{self.name}"


@dataclass(frozen=True)
class AppliedMigration:
    """A row of `schema_migrations`."""

    version: int
    name: str
    checksum: str


# --- pure ---------------------------------------------------------------------


def checksum(sql: str) -> str:
    """Hash the decoded text, not the raw bytes.

    `Path.read_text` normalizes newlines, so a checkout with autocrlf enabled
    produces the same digest as one without. Line endings are not a schema change.
    """
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def parse_filename(filename: str) -> tuple[int, str]:
    """Split `007_add_postings.sql` into `(7, "add_postings")`."""
    match = _FILENAME.match(filename)
    if match is None:
        raise MalformedMigrationNameError(
            f"{filename!r} is not a migration name. Expected NNN_name.sql, e.g. 002_postings.sql"
        )
    return int(match.group(1)), match.group(2)


def load_migration(path: Path) -> Migration:
    version, name = parse_filename(path.name)
    sql = path.read_text(encoding="utf-8")
    return Migration(version=version, name=name, path=path, sql=sql, checksum=checksum(sql))


def discover(directory: Path) -> list[Migration]:
    """Every `*.sql` in `directory`, ordered by version number.

    Sorted numerically, not lexicographically — `010` must follow `009`, and a
    plain string sort would put it before `002`.
    """
    if not directory.is_dir():
        raise MigrationError(f"migrations directory does not exist: {directory}")

    migrations = sorted(
        (load_migration(path) for path in directory.glob("*.sql")),
        key=lambda migration: migration.version,
    )

    seen: dict[int, Migration] = {}
    for migration in migrations:
        clash = seen.get(migration.version)
        if clash is not None:
            raise DuplicateMigrationVersionError(
                f"version {migration.version} claimed twice: "
                f"{clash.path.name} and {migration.path.name}"
            )
        seen[migration.version] = migration
    return migrations


def plan(discovered: list[Migration], applied: list[AppliedMigration]) -> list[Migration]:
    """Which migrations still need to run. Raises rather than guess on drift."""
    on_disk = {migration.version: migration for migration in discovered}
    in_db = {record.version: record for record in applied}

    for version, record in sorted(in_db.items()):
        migration = on_disk.get(version)
        if migration is None:
            raise MigrationDriftError(
                f"{version:03d}_{record.name} is recorded as applied but its file is gone. "
                "A migration that has run must stay in the repo; restore it from git."
            )
        if migration.checksum != record.checksum:
            raise MigrationDriftError(
                f"{migration.label} changed after it was applied. Applied migrations are "
                "immutable — revert the edit and add a new numbered migration instead."
            )

    pending = [migration for migration in discovered if migration.version not in in_db]
    if in_db and pending:
        highest = max(in_db)
        late = [migration.label for migration in pending if migration.version < highest]
        if late:
            raise MigrationDriftError(
                f"{', '.join(late)} would be applied out of order — "
                f"{highest:03d} has already run. Renumber above {highest:03d}."
            )
    return pending


# --- i/o ----------------------------------------------------------------------


def ensure_schema_migrations(conn: Connection) -> None:
    """The runner owns its own bookkeeping table, so no migration has to create it."""
    conn.execute(text(_SCHEMA_MIGRATIONS_DDL))


def fetch_applied(conn: Connection) -> list[AppliedMigration]:
    rows = conn.execute(
        text("SELECT version, name, checksum FROM schema_migrations ORDER BY version")
    ).all()
    return [
        AppliedMigration(version=int(row[0]), name=str(row[1]), checksum=str(row[2]))
        for row in rows
    ]


def apply_one(conn: Connection, migration: Migration) -> None:
    """Run one migration's SQL and record it.

    `exec_driver_sql` rather than `text()`: psycopg sends the file as-is, so a
    migration may contain several statements. `text()` would also try to read a
    literal colon in the SQL as a bind parameter.
    """
    conn.exec_driver_sql(migration.sql)
    conn.execute(
        text(
            "INSERT INTO schema_migrations (version, name, checksum)"
            " VALUES (:version, :name, :checksum)"
        ),
        {"version": migration.version, "name": migration.name, "checksum": migration.checksum},
    )


def run(engine: Engine, directory: Path | None = None) -> list[Migration]:
    """Apply every pending migration. Returns what was applied, in order.

    The whole run is one transaction. Postgres has transactional DDL, so a failure
    anywhere leaves the database exactly as it started — no half-migrated schema, and
    no `schema_migrations` row for a migration that did not finish. That also lets the
    advisory lock be transaction-scoped, so it cannot leak if the process dies.

    (A future migration needing `CREATE INDEX CONCURRENTLY` cannot run inside a
    transaction and would need its own path. Nothing needs that yet.)
    """
    discovered = discover(directory if directory is not None else default_migrations_dir())
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _LOCK_KEY})
        ensure_schema_migrations(conn)
        pending = plan(discovered, fetch_applied(conn))
        for migration in pending:
            apply_one(conn, migration)
    return pending


def status(
    engine: Engine, directory: Path | None = None
) -> tuple[list[AppliedMigration], list[Migration]]:
    """What has run and what has not. Raises on drift, exactly as `run` does."""
    discovered = discover(directory if directory is not None else default_migrations_dir())
    with engine.begin() as conn:
        ensure_schema_migrations(conn)
        applied = fetch_applied(conn)
    return applied, plan(discovered, applied)
