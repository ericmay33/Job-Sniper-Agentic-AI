# DECISIONS

Append-only. Never rewrite an entry — if a decision is reversed, add a new one that supersedes it.

Each entry: what was decided, and what it rules out. Short. This file tells an agent why the
code is shaped this way, so keep it to decisions that constrain future work.

---

### 2026-08-16 · Hard filters are SQL predicates, not vectors
Salary floor, location, YOE ceiling, role family are exact predicates, so a rejection reads
`requires 4 YOE` rather than a distance score.
**Rules out:** semantic filtering as the primary mechanism. Vectors serve "roles like ones I approved."

### 2026-08-16 · Scoring is absolute, never batch-relative
Fixed rubric against the stored constraint set. Batch-relative scores are incomparable across months.
**Rules out:** in-batch ranking as the source of truth. Ordering is a sort over absolute scores.

### 2026-08-16 · Abstention is a first-class output
A plausible fabricated address fails silently on send. Abstention rate is a headline metric.
**Rules out:** treating "no contact found" as a failure path or exception.

### 2026-08-16 · Confidence is deterministic
`strategy_base × verification_multiplier × name_role_match`, every factor logged.
**Rules out:** asking a model to rate its own confidence.

### 2026-08-16 · No agent loop in the resolver
The resolver cascade is a deterministic escalation ladder with a budget policy; reproducibility
depends on it. Reason-act belongs in `draft ↔ critique` and ambiguous page interpretation only.
**Rules out:** a general-purpose agent loop as the resolver's control flow.

### 2026-08-16 · Canonical role identity, not URL identity
Identity is `(normalized_company, role_family, location_bucket, req_id)`; raw URLs are stored
many-to-one in `sources`.
**Rules out:** keying exclusion state on URL — "never show me this again" would silently fail.

### 2026-08-16 · Decisions are append-only with reason codes
Reason codes: `comp`, `location`, `yoe`, `stack`, `company`, `timing`. Insert a row, never update one.
**Rules out:** mutable decision rows. The codes are what let the filter improve, not just remember.

### 2026-08-16 · No graph database yet
The schema stays relational but graph-shaped — edges as rows, not JSON blobs — so traversal is a
later addition rather than a migration.
**Rules out:** Neo4j or equivalent before the accumulated data justifies it.

### 2026-08-16 · Experience atoms, not resume PDFs
The grounding corpus is atomic experience records with skill tags and metrics, finer than bullets.
**Rules out:** embedding resume PDFs. Resume variants become queries over atoms.

### 2026-08-16 · Application submission stays manual
Automated submission is ToS-hostile and quality-destroying, and it solves the part that is already fast.
**Rules out:** any browser-automation submission path.

### 2026-08-22 · Run on Python 3.14, hold the code to 3.12
`.python-version` is 3.14; `requires-python` is `>=3.12`, so ruff and mypy target 3.12. The runtime
is convenience, the floor is the contract.
**Rules out:** 3.13/3.14-only syntax, and depending on whatever Python a machine happens to have.

### 2026-08-22 · The model provider is configuration, not a dependency
`LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` in env; no provider SDK in
`dependencies`. The first model call goes behind one narrow adapter.
**Rules out:** SDK types in the Pydantic contracts or at call sites. Swapping providers is an
adapter change, never a pipeline change.

### 2026-08-22 · Secret scanning is detect-secrets, not gitleaks
gitleaks' pre-commit hook is `language: golang` and TLS interception here breaks the Go bootstrap.
detect-secrets is pure Python. The baseline is deliberately empty, so any finding blocks the commit.
**Rules out:** an allowlist-by-accumulation baseline — a new baseline entry is a reviewed decision.

### 2026-08-22 · Postgres is a local native service, not a container
PostgreSQL 18.1 already runs as a Windows service on 5432, and a container cannot adopt an existing
native data directory.
**Rules out:** a `docker-compose.yml` here, and any assumption that the database is disposable —
the data directory is the asset. The cost is machine-specific setup, recorded in `STATE.md`.

### 2026-08-22 · SQLAlchemy Core, no ORM
Core gives connections, transactions, and parameter binding while the SQL stays hand-written, which
matters when filters are meant to be readable predicates.
**Rules out:** declarative models, sessions, lazy loading. Pydantic models stay the contract between
stages; they do not become table classes.

### 2026-08-22 · The application connects as the `postgres` superuser
Accepted for now: single user, single machine, local-only, and it removes a role-and-grant step
while the schema changes weekly.
**Revisit trigger:** (a) this DSN is first used by anything unattended, or (b) the database stops
being local-only. Either flips it to a least-privilege `jobsniper` role.

### 2026-08-22 · Migrations are forward-only, checksummed, one transaction
Numbered `NNN_name.sql` tracked in `schema_migrations` (`version`, `name`, `checksum`, `applied_at`),
which the runner creates itself. Three hard errors: a changed checksum on an applied migration, an
applied migration whose file vanished, a pending version below the high-water mark. The advisory
lock is transaction-scoped so it cannot leak.
**Rules out:** down migrations, editing an applied migration, back-filling a lower number, and —
for now — `CREATE INDEX CONCURRENTLY`, which cannot run inside a transaction.
