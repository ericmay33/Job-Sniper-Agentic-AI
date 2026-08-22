# DECISIONS

Append-only. Never rewrite an entry. If a decision is reversed, add a new entry that supersedes it and say why.

Each entry: what was decided, why, and what it rules out. This file exists so an agent (or a future you) understands *why* the code is shaped this way, not just that it is.

---

### 2026-08-16 · Hard filters are SQL predicates, not vectors
Salary floor, location, YOE ceiling, and role family are exact predicates. They must be explainable — a rejection reads `requires 4 YOE`, not a distance score.
**Rules out:** semantic filtering as the primary mechanism. Vector similarity is reserved for "roles like ones I approved."

### 2026-08-16 · Scoring is absolute, never batch-relative
Fixed rubric anchors scored against the stored constraint set. Batch-relative scores are incomparable across months and would destroy the longitudinal record.
**Rules out:** ranking by comparison within the current batch as the source of truth. Relative ordering is a sort over absolute scores.

### 2026-08-16 · Abstention is a first-class output
A plausible fabricated address fails silently on send, which is worse than no result. Abstention rate is a reported headline metric, not an error rate.
**Rules out:** treating "no contact found" as a failure path or exception.

### 2026-08-16 · Confidence is deterministic, not model-generated
Composed as `strategy_base × verification_multiplier × name_role_match`, all factors logged. Reproducibility is what makes the hit-rate number mean anything.
**Rules out:** asking a model to rate its own confidence.

### 2026-08-16 · No agent loop in the resolver
The resolver cascade is a deterministic escalation ladder with a budget policy. Making it agentic would destroy reproducibility. The reason-act loop belongs in `draft ↔ critique` and ambiguous page interpretation only.
**Rules out:** a general-purpose agent loop as the resolver's control flow.

### 2026-08-16 · Canonical role identity, not URL identity
The same req appears across multiple feeds under different titles and URLs. Identity is `(normalized_company, role_family, location_bucket, req_id)` with raw URLs stored many-to-one in `sources`.
**Rules out:** keying exclusion state on URL. Without this, "never show me this again" silently fails.

### 2026-08-16 · Decisions are append-only with reason codes
Reason code enum: `comp`, `location`, `yoe`, `stack`, `company`, `timing`. Insert a new row rather than updating an existing one.
**Rules out:** mutable decision rows. The reason codes are what let the filter improve over time rather than only remember.

### 2026-08-16 · No graph database yet
`company → team → person → role` is a genuine graph but earns nothing at current scale. Relational schema stays graph-shaped (edges as rows, not JSON blobs) so traversal is a later addition rather than a migration.
**Rules out:** Neo4j or equivalent before accumulated data justifies it.

### 2026-08-16 · Experience atoms, not resume PDFs
A resume is compressed skim-optimized prose — poor retrieval substrate. The grounding corpus is atomic experience records at finer-than-bullet granularity, with skill tags and metrics.
**Rules out:** embedding resume PDFs as the corpus. Resume variants become queries over atoms.

### 2026-08-16 · Application submission stays manual
Automated submission is ToS-hostile, quality-destroying, and solves the part that is already fast.
**Rules out:** any browser-automation submission path.
