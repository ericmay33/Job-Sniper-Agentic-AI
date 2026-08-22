"""Round-trip against a real Postgres.

Skipped unless `DATABASE_URL` is set and the server answers, so a checkout with no
database still runs a green suite.

These tests only ever move the configured database forward through the real
migrations — the same thing `jobsniper db migrate` does. Nothing here drops or
truncates anything.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from jobsniper.db import engine as db_engine
from jobsniper.db import migrate as db_migrate

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine():
    try:
        url = db_engine.database_url()
    except db_engine.MissingDatabaseURLError:
        pytest.skip("DATABASE_URL is not set")

    built = db_engine.create_db_engine(url)
    try:
        with built.connect():
            pass
    except SQLAlchemyError as exc:
        pytest.skip(f"database unreachable: {exc.__class__.__name__}")
    return built


@pytest.fixture(scope="module")
def migrated(engine):
    db_migrate.run(engine)
    return engine


def test_second_run_applies_nothing(migrated):
    assert db_migrate.run(migrated) == []


def test_001_is_recorded_as_applied(migrated):
    applied, pending = db_migrate.status(migrated)

    assert 1 in {record.version for record in applied}
    assert pending == []


def test_recorded_checksum_matches_the_file_on_disk(migrated):
    applied, _ = db_migrate.status(migrated)
    on_disk = {
        m.version: m.checksum for m in db_migrate.discover(db_engine.default_migrations_dir())
    }

    for record in applied:
        assert record.checksum == on_disk[record.version]


def test_pgvector_is_enabled(migrated):
    with migrated.connect() as conn:
        version = conn.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()

    assert version is not None, "001_init should have enabled pgvector"


def test_check_connection_reports_vector(migrated):
    info = db_engine.check_connection(migrated)

    assert info.version.startswith("PostgreSQL")
    assert info.has_extension("vector")
