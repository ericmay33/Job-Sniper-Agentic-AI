"""Command-line entry point.

Subcommands are added alongside the stages that implement them, not in advance.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from jobsniper import __version__
from jobsniper.db import engine as db_engine
from jobsniper.db import migrate as db_migrate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobsniper",
        description="Stateful job-search pipeline. Nothing sends without explicit approval.",
    )
    parser.add_argument("--version", action="version", version=f"jobsniper {__version__}")

    commands = parser.add_subparsers(dest="command")
    db = commands.add_parser("db", help="database connection and migrations")
    db.set_defaults(db_parser=db)

    db_commands = db.add_subparsers(dest="db_command")
    db_commands.add_parser("check", help="connect and report server version and extensions")

    for name, help_text in (
        ("migrate", "apply every pending migration"),
        ("status", "show which migrations have been applied"),
    ):
        sub = db_commands.add_parser(name, help=help_text)
        sub.add_argument(
            "--migrations-dir",
            type=Path,
            default=None,
            metavar="DIR",
            help="override the migrations directory (default: migrations/ at the repo root)",
        )

    return parser


def _check(args: argparse.Namespace) -> int:
    url = db_engine.database_url()
    info = db_engine.check_connection(db_engine.create_db_engine(url))
    print(f"url        {db_engine.safe_url(url)}")
    print(f"server     {info.version.split(' on ')[0]}")
    print(f"extensions {', '.join(f'{n} {v}' for n, v in info.extensions)}")
    if not info.has_extension("vector"):
        print(
            "\npgvector is not enabled in this database. Run `jobsniper db migrate`; "
            "if that fails, pgvector is not installed into the server itself.",
            file=sys.stderr,
        )
        return 1
    return 0


def _migrate(args: argparse.Namespace) -> int:
    engine = db_engine.create_db_engine()
    applied = db_migrate.run(engine, args.migrations_dir)
    if not applied:
        print("nothing to apply — the database is up to date")
        return 0
    for migration in applied:
        print(f"applied {migration.label}")
    return 0


def _status(args: argparse.Namespace) -> int:
    engine = db_engine.create_db_engine()
    applied, pending = db_migrate.status(engine, args.migrations_dir)

    print("applied")
    for record in applied:
        print(f"  {record.version:03d}_{record.name}")
    if not applied:
        print("  (none)")

    print("pending")
    for migration in pending:
        print(f"  {migration.label}")
    if not pending:
        print("  (none)")
    return 0


_DB_COMMANDS = {"check": _check, "migrate": _migrate, "status": _status}


def _run_db_command(args: argparse.Namespace) -> int:
    handler = _DB_COMMANDS[args.db_command]
    try:
        return handler(args)
    except (db_engine.MissingDatabaseURLError, db_migrate.MigrationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        # The DSN carries a password; SQLAlchemy's own message does not include it,
        # but keep this to the driver's text rather than echoing any config back.
        print(f"database error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "db":
        if args.db_command is None:
            args.db_parser.print_help()
            return 0
        return _run_db_command(args)

    parser.print_help()
    return 0
