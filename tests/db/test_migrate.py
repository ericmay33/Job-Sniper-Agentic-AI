"""Tests for the pure half of the migration runner — no database involved.

`discover` and `plan` hold every branch that can silently corrupt the schema
record, so they are the part that has to be tested exhaustively.
"""

import pytest

from jobsniper.db.migrate import (
    AppliedMigration,
    DuplicateMigrationVersionError,
    MalformedMigrationNameError,
    MigrationDriftError,
    MigrationError,
    checksum,
    discover,
    load_migration,
    parse_filename,
    plan,
)


def write(directory, filename, body="SELECT 1;\n"):
    path = directory / filename
    path.write_text(body, encoding="utf-8")
    return path


def applied_from(migration, checksum_override=None):
    """The `schema_migrations` row that running `migration` would have written."""
    return AppliedMigration(
        version=migration.version,
        name=migration.name,
        checksum=checksum_override or migration.checksum,
    )


# --- filenames ---------------------------------------------------------------


def test_parse_filename_splits_version_from_name():
    assert parse_filename("007_add_postings.sql") == (7, "add_postings")


@pytest.mark.parametrize(
    "filename",
    ["init.sql", "001.sql", "001-init.sql", "abc_init.sql", "001_init.txt", "001_.sql"],
)
def test_parse_filename_rejects_malformed_names(filename):
    with pytest.raises(MalformedMigrationNameError):
        parse_filename(filename)


# --- discover ----------------------------------------------------------------


def test_discover_orders_numerically_not_lexicographically(tmp_path):
    # The case that a plain string sort gets wrong: "010" sorts before "002".
    for filename in ("010_ten.sql", "002_two.sql", "001_one.sql"):
        write(tmp_path, filename)

    assert [m.version for m in discover(tmp_path)] == [1, 2, 10]


def test_discover_rejects_duplicate_versions(tmp_path):
    write(tmp_path, "001_one.sql")
    write(tmp_path, "1_also_one.sql")

    with pytest.raises(DuplicateMigrationVersionError):
        discover(tmp_path)


def test_discover_rejects_a_malformed_file(tmp_path):
    write(tmp_path, "001_one.sql")
    write(tmp_path, "notes.sql")

    with pytest.raises(MalformedMigrationNameError):
        discover(tmp_path)


def test_discover_ignores_non_sql_files(tmp_path):
    write(tmp_path, "001_one.sql")
    (tmp_path / "README.md").write_text("not a migration", encoding="utf-8")

    assert [m.version for m in discover(tmp_path)] == [1]


def test_discover_on_missing_directory_is_an_error(tmp_path):
    with pytest.raises(MigrationError):
        discover(tmp_path / "nope")


def test_checksum_ignores_line_endings(tmp_path):
    # Same SQL checked out with and without autocrlf must not read as a change.
    (tmp_path / "001_unix.sql").write_bytes(b"SELECT 1;\n")
    (tmp_path / "002_windows.sql").write_bytes(b"SELECT 1;\r\n")

    assert load_migration(tmp_path / "001_unix.sql").checksum == (
        load_migration(tmp_path / "002_windows.sql").checksum
    )


def test_checksum_changes_when_sql_changes():
    assert checksum("SELECT 1;") != checksum("SELECT 2;")


# --- plan --------------------------------------------------------------------


def test_plan_with_nothing_applied_returns_everything(tmp_path):
    write(tmp_path, "001_one.sql")
    write(tmp_path, "002_two.sql")
    discovered = discover(tmp_path)

    assert plan(discovered, []) == discovered


def test_plan_with_everything_applied_is_empty(tmp_path):
    write(tmp_path, "001_one.sql")
    discovered = discover(tmp_path)

    assert plan(discovered, [applied_from(discovered[0])]) == []


def test_plan_returns_only_the_unapplied_tail(tmp_path):
    write(tmp_path, "001_one.sql")
    write(tmp_path, "002_two.sql")
    discovered = discover(tmp_path)

    assert plan(discovered, [applied_from(discovered[0])]) == [discovered[1]]


def test_plan_rejects_an_edited_applied_migration(tmp_path):
    write(tmp_path, "001_one.sql")
    discovered = discover(tmp_path)
    stale = applied_from(discovered[0], checksum_override=checksum("what it used to say"))

    with pytest.raises(MigrationDriftError, match="immutable"):
        plan(discovered, [stale])


def test_plan_rejects_an_applied_migration_whose_file_is_gone(tmp_path):
    write(tmp_path, "001_one.sql")
    discovered = discover(tmp_path)
    vanished = AppliedMigration(version=2, name="two", checksum=checksum("SELECT 1;\n"))

    with pytest.raises(MigrationDriftError, match="file is gone"):
        plan(discovered, [vanished])


def test_plan_rejects_a_migration_inserted_below_the_high_water_mark(tmp_path):
    # 002 has run; 001 shows up afterwards from a stale branch. Applying it now
    # would produce a schema no fresh database could ever reproduce.
    write(tmp_path, "001_one.sql")
    write(tmp_path, "002_two.sql")
    discovered = discover(tmp_path)

    with pytest.raises(MigrationDriftError, match="out of order"):
        plan(discovered, [applied_from(discovered[1])])
