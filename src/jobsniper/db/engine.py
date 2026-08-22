"""Engine construction. `DATABASE_URL` is the only database configuration input.

The URL stored in `.env` is a plain Postgres DSN. Which DBAPI driver we use to
speak to that server is an implementation detail of this package, not something
the operator should have to encode in the URL, so the driver is normalized here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url

#: The DBAPI SQLAlchemy should use. psycopg 3, never psycopg2.
_DRIVER = "postgresql+psycopg"

#: Bare schemes we rewrite onto `_DRIVER`. Anything else is left alone so an
#: operator can deliberately pin a different driver.
_BARE_SCHEMES = frozenset({"postgresql", "postgres"})


class MissingDatabaseURLError(RuntimeError):
    """`DATABASE_URL` is unset, so there is nothing to connect to."""

    def __init__(self) -> None:
        super().__init__(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in "
            "(see docs/STATE.md for the local Postgres setup)."
        )


@dataclass(frozen=True)
class ServerInfo:
    """What `jobsniper db check` reports back."""

    version: str
    extensions: tuple[tuple[str, str], ...]

    def has_extension(self, name: str) -> bool:
        return any(ext == name for ext, _ in self.extensions)


def database_url() -> URL:
    """Read `DATABASE_URL` and normalize it onto psycopg 3.

    Real environment variables win over `.env`; that is python-dotenv's default
    and it is what makes CI and one-off overrides work.
    """
    load_dotenv(find_dotenv(usecwd=True))
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raise MissingDatabaseURLError
    url = make_url(raw)
    if url.drivername in _BARE_SCHEMES:
        url = url.set(drivername=_DRIVER)
    return url


def safe_url(url: URL) -> str:
    """Renderable form of a URL. The DSN carries a password — never log the raw one."""
    return url.render_as_string(hide_password=True)


def create_db_engine(url: URL | None = None) -> Engine:
    """Build an Engine. Pool defaults are fine: this is a single-user batch tool."""
    return create_engine(url if url is not None else database_url())


def check_connection(engine: Engine) -> ServerInfo:
    """Connect and report what the server is and which extensions are installed."""
    with engine.connect() as conn:
        version = cast(str, conn.execute(text("SELECT version()")).scalar_one())
        rows = conn.execute(
            text("SELECT extname, extversion FROM pg_extension ORDER BY extname")
        ).all()
    extensions = tuple((cast(str, r[0]), cast(str, r[1])) for r in rows)
    return ServerInfo(version=version, extensions=extensions)


def default_migrations_dir() -> Path:
    """`migrations/` at the repo root.

    This is a personal tool run from its own checkout, so a path relative to the
    package is correct and predictable. The CLI exposes an override for anything else.
    """
    return Path(__file__).resolve().parents[3] / "migrations"
