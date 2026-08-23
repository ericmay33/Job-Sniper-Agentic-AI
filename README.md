# Job Sniper

A stateful job-search pipeline: discovery and filtering over trusted feeds, contact resolution,
grounded outreach drafting, and human approval before anything sends.

The core asset is the accumulated state, not the agent — every approve, reject, apply, and reply is
a labeled event.

## Docs

- `docs/STATE.md` — what exists right now and the next action. Read this first.
- `docs/SPEC.md` — the full specification.
- `docs/DECISIONS.md` — why the code is shaped this way (append-only).
- `AGENTS.md` — guidance for coding agents, including the non-negotiable invariants.

## Quickstart

```
uv sync                     install deps
uv run pytest               tests
uv run ruff check .         lint
uv run ruff format .        format
uv run mypy src             types
uv run jobsniper --help     CLI
```

Copy `.env.example` to `.env` and fill it in. This repo is public: secrets are env-based only, and
a pre-commit secret scanner runs on every commit.

## Database

PostgreSQL with [pgvector](https://github.com/pgvector/pgvector), running as a local native
service — there is no container here. Migrations are numbered SQL files under `migrations/`,
applied forward-only and checksummed; an applied migration is immutable.

```
uv run jobsniper db check     server version + installed extensions
uv run jobsniper db status    applied vs pending migrations
uv run jobsniper db migrate   apply pending migrations
```

Setup is machine-specific and recorded in `docs/STATE.md`. On Windows, pgvector has no prebuilt
binary and must be compiled with MSVC against the installed Postgres major version.

Tests that need a live database are marked `integration` and skip when `DATABASE_URL` is unset or
unreachable, so `uv run pytest` is green on a fresh checkout with no database.
