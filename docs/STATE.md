# STATE

**Updated at breadcrumb, every session. Agents read this file first.**
Keep it under one screen. This is current state, not history — history lives in git and `DECISIONS.md`.

---

## Last updated
2026-08-22

## What exists and works
- Python scaffolding: `pyproject.toml` (hatchling, src layout), `.python-version` (3.14), `uv.lock`.
  Tooling green: `uv run pytest`, `ruff check`, `ruff format --check`, `mypy src`.
  Pre-commit with detect-secrets proven by negative test; `.secrets.baseline` is empty.
- **Database layer, code-complete and tested.** `db/engine.py` reads `DATABASE_URL`, normalizes
  the DSN onto psycopg 3, exposes `check_connection`. `db/migrate.py` is a forward-only runner:
  numbered `NNN_name.sql` files tracked in `schema_migrations`, whole run in one transaction
  under a transaction-scoped advisory lock. SQLAlchemy Core, no ORM.
- **Drift is enforced in code, not just documented** — an edited applied migration, an applied
  migration whose file vanished, and a migration numbered below the high-water mark are all
  hard errors. 22 unit tests cover the pure half (`discover`, `plan`, filename parsing,
  checksum) with no database involved.
- `migrations/001_init.sql` — enables pgvector, nothing else.
- CLI: `jobsniper db check | migrate | status`, all exiting non-zero on failure. Verified that
  a missing `DATABASE_URL` and a bad DSN both produce a clean error with no password echoed.
- Integration tests (`-m integration`) skip when `DATABASE_URL` is unset or unreachable, so a
  fresh checkout with no database still runs green.

## What is half-built
- **The database server side is not stood up yet.** The Python code is finished and staged;
  pgvector is not compiled, the `jobsniper` database does not exist, and `001` has never run.
  Everything needed to fix that is the breadcrumb below.

## What is next

**First physical action for the next session:** open an Administrator "x64 Native Tools
Command Prompt for VS 2022" and build pgvector. Everything below is one unbroken sequence —
do not start on `models/` until `db migrate` is a no-op on the second run.

1. **Install VS Build Tools**, "Desktop development with C++" workload —
   <https://visualstudio.microsoft.com/visual-cpp-build-tools/>
   Currently absent: `vswhere.exe` does not exist on this machine.
2. **Build pgvector**, from an **Administrator** x64 Native Tools prompt (the install step
   writes into `C:\Program Files`):
   ```
   set "PGROOT=C:\Program Files\PostgreSQL\18"
   cd %TEMP%
   git clone --branch v0.8.6 https://github.com/pgvector/pgvector.git
   cd pgvector
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```
   Done when `C:\Program Files\PostgreSQL\18\share\extension\vector.control` exists.
   If `git clone` fails on a certificate: `git config --global http.sslBackend schannel`.
3. **Create the database:**
   `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE jobsniper;"`
4. **Create `.env`** with a single `DATABASE_URL=` line. Copy the DSN from `.env.example` and
   insert the superuser password between `postgres` and the `@`. `.env` is gitignored.
   Do not write a filled-in DSN anywhere tracked, including this file — detect-secrets blocks
   that shape of URL on sight, which is the intended behaviour.

**Then verify, in this order:**
```
uv run jobsniper db check      # server version + extension list
uv run jobsniper db migrate    # applies 001_init
uv run jobsniper db migrate    # MUST print "nothing to apply"
uv run pytest -m integration   # 5 tests, no longer skipped
Restart-Service postgresql-x64-18
uv run jobsniper db status     # 001 still applied — bookkeeping survived the restart
```
Then the drift check, which proves the invariant is real: append a comment line to the
already-applied `migrations/001_init.sql`, run `db migrate`, confirm it **fails** with a
checksum error, then revert the file.

**Once that is green, the actual session work:** create `src/jobsniper/models/posting.py` and
define the canonical `Posting` Pydantic contract, keyed on
`(normalized_company, role_family, location_bucket, req_id)` per `DECISIONS.md`. This is
**human-written** (`AGENTS.md` division of labor) — the agent proposes fields and critiques,
and writes the tests alongside it. Its table lands in `migrations/002_postings.sql` in the
same commit.

## Known friction / open questions
- **Postgres is machine-specific.** Native PostgreSQL 18.1, service `postgresql-x64-18`,
  root `C:\Program Files\PostgreSQL\18`, port 5432, scram-sha-256. `psql.exe` is in
  `...\18\bin` and **not on PATH**. The repo cannot recreate this — the accepted cost of not
  using a container (`DECISIONS.md`).
- **pgvector has no Windows binary.** It must be compiled with MSVC against each Postgres
  major version. A future PG upgrade means rebuilding it, or `001` fails on a fresh database.
- **The app connects as the `postgres` superuser** — deliberate, with a revisit trigger
  recorded in `DECISIONS.md`. Not a permanent state.
- **TLS interception on this machine.** `[tool.uv] system-certs = true` makes `uv` work;
  `go.dev/dl` still fails, which is why the secret scanner is detect-secrets not gitleaks.
  Same risk applies to the Build Tools download and `git clone`.
- Files created via PowerShell `>` are UTF-16 and break the build. Write UTF-8 explicitly.
- `uv` lives at `~/.local/bin` and may not be on PATH until a shell restart.
- Open: which model provider gets the first adapter.

---

## Session log

Newest first. Three fields, one line each.

| Date | Ran | Payload | Friction |
|---|---|---|---|
| 2026-08-22 | Day 2 persistence | SQLAlchemy Core + psycopg 3 deps, `db/engine.py`, forward-only checksummed migration runner, `001_init.sql`, `db check/migrate/status` CLI, 22 unit + 5 integration tests | Native PG18 already held 5432, so Docker was dropped; pgvector ships no Windows binary and needs an MSVC build not yet installed, so the server side is unverified |
| 2026-08-22 | Day 1 scaffolding | uv project, ruff/mypy/pytest config, pre-commit + secret scanning proven by negative test, package skeleton | TLS interception blocked uv and the gitleaks Go bootstrap; README was UTF-16 |
