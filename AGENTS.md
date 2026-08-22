# AGENTS.md

Guidance for coding agents (Claude Code, Cursor) working in this repo.

**Read `docs/STATE.md` first** — it says what exists right now and what the next action is.
Full spec: `docs/SPEC.md`. Why the code is shaped this way: `docs/DECISIONS.md` (append-only).

---

## What this is

Job Sniper: a stateful job-search pipeline. Discovery and filtering over trusted feeds, contact resolution, grounded outreach drafting, human approval before anything sends.

**The core asset is accumulated state, not the agent.** Every approve, reject, apply, and reply is a labeled event. Code that discards or fails to persist a user decision is a bug, regardless of whether tests pass.

---

## Non-negotiable invariants

Violating any of these is a defect even if the code works. If a request conflicts with one, say so instead of complying.

1. **Never invent a contact.** No fabricated names, emails, or titles. If resolution fails, abstain.
2. **Abstention is a valid return value**, not an error or exception. `{abstained: true, confidence: 0.2}` is correct output.
3. **Confidence is deterministic** — composed arithmetically from logged factors, never produced by a model.
4. **Nothing sends without explicit human approval.** No auto-send path may exist, even behind a flag.
5. **Hard filters are SQL predicates**, not model calls. A rejection must read `requires 4 YOE`, never a similarity score.
6. **Scores are absolute**, against a fixed rubric — never relative to the current batch.
7. **Untrusted scraped content never shares context with tool-authorization decisions.** Mail parameters resolve outside the model path.
8. **No secrets in the repo.** This repo is public. Env-based only.

---

## Layout

```
src/jobsniper/
  models/      Pydantic schemas — the typed contracts between stages
  db/          Connection, queries, migration runner
  discovery/   Fetch, canonicalize, filter, extract, score
  eval/        Golden sets, metrics, runners
  cli.py       Entry point
tests/         Mirrors src layout
migrations/    Numbered SQL, forward-only
docs/          SPEC.md, STATE.md, DECISIONS.md
```

Create directories when a component is actually being built, not in advance.

---

## Commands

```
uv sync                     install deps
uv run pytest               tests
uv run ruff check .         lint
uv run ruff format .        format
uv run mypy src             types
docker compose up -d        start postgres
uv run jobsniper <cmd>      CLI
```

Never invoke `pip` directly. Dependencies go through `uv`.

---

## Conventions

- Python 3.12+. `ruff` for lint and format. `mypy` strict on `models/` and `db/`, normal elsewhere.
- Pydantic models are the contract between stages. Change one, update its tests in the same commit.
- Migrations are forward-only and numbered. Never edit an applied migration.
- Keep modules small enough that a diff fits on one screen.
- Tests required for anything with branching logic. Confidence composition and filter predicates are the correctness core — they always get tests.
- Prefer one complete, committed, working change over a broad unfinished one. Sessions are ~55 minutes.

---

## Division of labor

**Human writes:** Pydantic contracts, confidence composition, filter predicates, schema design. These are the learning surface of this project. Propose and critique them; do not author them unprompted.

**Agent writes:** test scaffolding, CLI plumbing, migration boilerplate, refactors, docstrings, config.

Use plan mode before multi-file changes. Propose, wait for approval, then write.

---

## End of session

When asked to close out a session:

1. Update `docs/STATE.md` following its template — what exists, what's half-built, the **one concrete first physical action** for next session (a file and a change, not a topic), and any friction.
2. Append any design decision made today to `docs/DECISIONS.md`: what was decided, why, what it rules out. Never rewrite existing entries.
3. Do not modify `AGENTS.md` unless repo structure or an invariant actually changed.
