# STATE

**Agents read this file first.** This is current state, not history — history lives in git
and `DECISIONS.md`.

Keep it under one screen. Record only what changes how the next session acts. Not code
structure, not file inventories, not rationale — those live in the code, `SPEC.md`, and
`DECISIONS.md`. If a note would not change someone's first action, leave it out.

---

## Last updated
2026-08-23

## What exists and works
- Tooling green: `pytest` (27), `ruff`, `mypy src`, pre-commit with detect-secrets.
- **Database is live and verified end to end.** PostgreSQL 18.1 + pgvector 0.8.6, database
  `jobsniper`, `001_init` applied. `db check | migrate | status` all work, a second `migrate`
  is a no-op, and an edited applied migration is rejected on checksum.
- `db/` is SQLAlchemy Core over psycopg 3: `engine.py` (DSN handling, `check_connection`),
  `migrate.py` (forward-only, checksummed, one transaction, advisory-locked).
- No tables yet. The schema starts with the first Pydantic contract.

## Environment (machine-specific — the repo cannot recreate this)
- Native Windows service `postgresql-x64-18`, port 5432, root `C:\Program Files\PostgreSQL\18`.
  `psql.exe` lives in `...\18\bin` and is not on PATH. pgAdmin 4 installed for browsing.
- pgvector was built from source with MSVC; no Windows binary exists. A Postgres major
  upgrade means rebuilding it or `001` fails on a fresh database.
- `.env` holds `DATABASE_URL` and is gitignored. Never put a filled-in DSN in a tracked file.

## What is half-built
Nothing.

## What is next

**First physical action:** create `docs/ARCHITECTURE.md` and draw the system as a Mermaid
diagram — the five stages from `SPEC.md` as boxes, what each consumes and emits, which are
deterministic vs. model-backed, and which exist today (nothing past `db/`). The point is a map
where "what can we finish this session" is answerable by pointing at a box.

**Then the first real schema, same session** — this is where the architecture becomes tables.

1. Name the entity set off the diagram before writing SQL. Expected shape: `companies`,
   `postings` (canonical roles), `sources` (raw feed URLs, many-to-one onto a posting),
   `decisions` (append-only, reason codes). **Not** `contacts` or `outcomes` — those are
   Stage 4/5 and are deliberately later.
2. Canonical identity is `(normalized_company, role_family, location_bucket, req_id)`
   (`DECISIONS.md`), so `postings` carries the uniqueness constraint on it and `sources` hangs
   off it. That constraint is what makes "never show me this again" actually work.
3. The Pydantic contract and its table land in the same commit:
   `src/jobsniper/models/posting.py` + `migrations/002_postings.sql`, tests alongside.

**Division of labor holds** (`AGENTS.md`): schema and Pydantic contracts are human-written. The
agent proposes fields, critiques them, and writes the tests and migration boilerplate.

**Done when:** `db migrate` applies `002`, a second run is a no-op, and a `Posting` round-trips
through the table in an integration test.

---

## Session log

Newest first. Three fields, one line each.

| Date | Ran | Payload | Friction |
|---|---|---|---|
| 2026-08-23 | Day 3 database stood up | VS Build Tools + pgvector 0.8.6 compiled and installed, `jobsniper` database created, `.env` wired, `001_init` applied, drift check proven to fail on a tampered file, 27 tests green including 5 integration; pgAdmin 4 added | None |
| 2026-08-22 | Day 2 persistence | SQLAlchemy Core + psycopg 3 deps, `db/engine.py`, forward-only checksummed migration runner, `001_init.sql`, `db check/migrate/status` CLI, 22 unit + 5 integration tests | Native PG18 already held 5432, so Docker was dropped; pgvector ships no Windows binary and needed an MSVC build |
| 2026-08-22 | Day 1 scaffolding | uv project, ruff/mypy/pytest config, pre-commit + secret scanning proven by negative test, package skeleton | TLS interception blocked uv and the gitleaks Go bootstrap; README was UTF-16 |
