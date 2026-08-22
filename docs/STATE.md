# STATE

**Updated at breadcrumb, every session. Agents read this file first.**
Keep it under one screen. This is current state, not history — history lives in git and `DECISIONS.md`.

---

## Last updated
2026-08-22

## What exists and works
- Python project scaffolding: `pyproject.toml` (hatchling, src layout), `.python-version` (3.14),
  `uv.lock`. `uv sync` installs the `dev` group with no flags.
- Tooling, all verified green: `uv run pytest` (2 smoke tests), `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy src`.
- mypy is strict globally and relaxed per-module for `discovery/`, `eval/`, `cli`, `tests` —
  verified by test: an untyped def in `models/` errors, the same def in `discovery/` does not.
- Pre-commit installed and proven: ruff-check, ruff-format, detect-secrets, detect-private-key,
  check-added-large-files. A staged file containing a fake AWS key is **blocked** (exit 1).
- `.gitignore`, `.env.example` (provider-agnostic LLM config), `.secrets.baseline` (empty).
- Package skeleton: `src/jobsniper/{__init__,cli}.py` and `{models,db,discovery,eval}/__init__.py`.
  `uv run jobsniper --help` / `--version` work. No subcommands yet.

## What is half-built
- (nothing) — `models/`, `db/`, `discovery/`, `eval/`, and `migrations/` are empty placeholders.

## What is next
**First physical action for the next session:**
- Create `src/jobsniper/models/posting.py` and define the canonical `Posting` Pydantic contract,
  keyed on `(normalized_company, role_family, location_bucket, req_id)` per `DECISIONS.md`.
  This is **human-written** (`AGENTS.md` division of labor) — the agent proposes fields and
  critiques, and writes the tests alongside it.

## Known friction / open questions
- **TLS interception on this machine.** The Windows cert store serves a malformed CA, so `uv`
  needs system certs (`[tool.uv] system-certs = true`, now in `pyproject.toml`, so plain
  `uv sync` works). `go.dev/dl` still fails cert verification, which is why the secret scanner is
  detect-secrets rather than gitleaks — see `DECISIONS.md`.
- `README.md` was UTF-16 (PowerShell-created) and broke the hatchling build until rewritten as
  UTF-8. Watch for this on any file created via `>` in PowerShell.
- `uv` lives at `~/.local/bin` and may not be on PATH until a shell restart.
- Open: which model provider gets the first adapter, and whether `db/` uses psycopg directly.

---

## Session log

Newest first. Three fields, one line each.

| Date | Ran | Payload | Friction |
|---|---|---|---|
| 2026-08-22 | Day 1 scaffolding | uv project, ruff/mypy/pytest config, pre-commit + secret scanning proven by negative test, package skeleton | TLS interception blocked uv and the gitleaks Go bootstrap; README was UTF-16 |
