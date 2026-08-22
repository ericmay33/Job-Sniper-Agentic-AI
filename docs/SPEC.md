# JOB SNIPER — FINAL SPEC
**v2.0 · 2026-08-16 · Supersedes MASTER_CONTEXT v1.0**

v1.0 deferred discovery ("supply is solved"). Live operation disproved that: supply of *listings* is solved, supply of roles that survive real constraints is not. A stateless search returns roles already applied to and roles that fail on salary, location, or years-of-experience. Discovery moves to stage one — not as an autonomous role-hunter, but as a **stateful filter over trusted feeds**.

Everything else in v1.0 holds: abstention as a first-class output, deterministic confidence, evals from commit one, human gate before any send.

---

## 1. WHAT IT IS

A stateful job-search operating system. Five stages, one accumulating knowledge base, a human decision point at every stage that touches the outside world.

**The core asset is not the agent. It is the state.** Every approve, reject, apply, and reply is a labeled event. After two months that's several hundred labeled decisions about what this specific user wants. That is what makes the system's output better than a fresh LLM query, and it is the one component that cannot be reproduced by someone spinning up the same framework.

---

## 2. THE FIVE STAGES

### Stage 1 — Discovery & Filter
**In:** trusted feeds (Jobright, Simplify, SimplifyJobs/New-Grad-Positions repo, LinkedIn, company boards) + stored user constraints + full history of prior decisions.
**Out:** a small ranked shortlist of roles never before seen, each with a structured summary and an absolute fit score.

Pipeline: fetch → **canonicalize** → filter (hard predicates) → extract → score → rank.

**Canonicalization is the hard engineering here.** The same Palantir FDE req appears on Lever, in the GitHub repo, on Jobright, and on careers.palantir.com under three different titles. Identity keyed on URL fails immediately. Canonical identity is `(normalized_company, role_family, location_bucket, req_id?)` with fuzzy matching on title. Without this, "never show me this again" silently doesn't work.

**Hard filters are SQL predicates, not vectors.** Salary floor, location allowlist, max tolerated YOE, role families in/out, new-grad language present. Exact and explainable — a rejection reads "requires 4 YOE" not "cosine distance 0.31."

**Per-role summary card:** company, role family, comp (parsed range or explicitly unknown), location + remote policy, YOE requirement, stack, new-grad-program signal, company size/stage, why-surfaced, and the fit score with its component breakdown.

### Stage 2 — Human Triage
Approve / reject / defer, one keystroke each. Rejection captures a reason code (comp, location, YOE, stack, company, timing). Both directions persist permanently.

Rejections feed the exclusion set. Approvals feed the preference model. The reason codes are what make Stage 1 improve over time rather than just remember.

### Stage 3 — Application (manual, by design)
User applies in a browser. System tracks status. Automated application submission is permanently out of scope — it's ToS-hostile, quality-destroying, and the part that is actually fast already.

### Stage 4 — Outreach Loop
Runs over applied roles, in batch.

**4a. Contact targeting.** Who to reach is a function of company shape: at a <50-person startup, a founder or eng lead; at mid-size, the hiring manager or a team engineer; at enterprise, the recruiter owning the req plus one engineer on the team. This targeting rubric is explicit and stored, not implied by a prompt.

**4b. Contact resolution.** Four-tier cascade, escalating only on failure:
- T0 cache (compounds across months, free)
- T1 free public: posting metadata, team pages, GitHub org/commit metadata, engineering blog bylines, conference bios, `security.txt`
- T2 pattern inference from a known public address + MX/deliverability verification
- T3 vendor API (Hunter/Apollo-class free tiers), budget-metered, last resort

Confidence is deterministic: `strategy_base × verification_multiplier × name_role_match`, all three logged. **Abstention is a valid, valuable output** — a plausible fabricated address is worse than nothing because mail to a dead address fails silently.

**4c. Contact ranking + approval.** Ranked candidates with evidence links, user approves the target.

**4d. Draft.** Short outreach grounded strictly in retrieved experience atoms, with a citation map: every claim traced to an atom ID. Uncitable claims are structurally rejected, not stylistically discouraged. Prior sent drafts retrieved to prevent recycled openers.

**4e. Gate + send.** Durable human interrupt — the run survives process death and a three-day pause. Approve / edit / reject-with-feedback (which re-enters the drafter). Only then does the mail tool send, under daily and per-company caps. Auto-send is permanently off.

### Stage 5 — Batch Close
Persist outcomes, schedule follow-ups (time-triggered, never model-triggered), expire stale scraped context, update the preference model, emit the weekly report: resolver hit rate, abstention rate, reply rate by confidence band, cost per reply, funnel conversion.

---

## 3. THE KNOWLEDGE LAYER

**User corpus — experience atoms.** Resumes are parsed as a *seed*, then enriched into atomic records: one accomplishment, decision, or technical detail each, finer-grained than a resume bullet, including what a resume can't hold (why a decision was made, what the alternative was, what broke, real numbers). Each atom carries skill tags, metrics, date range, and variant affinity.

Resume PDFs are not the corpus. A resume is six-second-skim compressed prose — the worst possible retrieval substrate. The atoms are.

**Resume variants become queries over atoms, not stored files.** This is where the "stash multiple resumes and pick one" idea lands — absorbed into the retrieval layer, so it scales to per-application bullet assembly at zero additional architecture.

**What's embedded vs. not:**

| Data | Embedded | Why |
|---|---|---|
| Experience atoms | Yes | Grounding for fit + drafts |
| Job postings | Yes | "Roles like ones I approved" |
| Scraped company pages | Yes, TTL'd | Personalization; stales fast |
| Prior sent drafts | Yes | Style consistency, anti-repetition |
| Constraints, decisions, contacts, outcomes | **No** | Predicates and analytics — SQL, exactly and explainably |

**No graph database.** `company → team → person → role` is a real graph but earns nothing at current scale. Keep the relational schema graph-shaped (edges as rows, not JSON blobs) so traversal is a later addition rather than a migration.

---

## 4. AGENT ARCHITECTURE

**Where the reason-act loop belongs — and where it doesn't.** The resolver cascade is a deterministic escalation ladder with a budget policy, *not* a ReAct loop. Making it agentic would destroy reproducibility and with it the meaning of the hit-rate number. The loop belongs in exactly two places: `draft ↔ critique` (bounded at 2 iterations) and interpretation of ambiguous scraped contact pages.

**Deterministic vs. model, by component:**

| Component | Deterministic | Model |
|---|---|---|
| Canonicalization | Normalization + fuzzy match | — |
| Hard filters | SQL predicates | — |
| Extraction | Pydantic schema enforcement | Field extraction |
| Fit score | Requirement coverage vs. skill tags | Soft fit + gap list |
| Contact targeting | Company-shape rubric | — |
| Contact resolution | Cascade + confidence composition | Page interpretation only |
| Drafting | Citation validation | Generation |
| Critique | Iteration bound | Judgment |

**Scoring is absolute, never batch-relative.** Fixed rubric anchors, scored against the constraint set — not against the other nine roles that happened to appear Tuesday. Batch-relative scores are incomparable across months and would destroy the longitudinal record. Relative ranking is then a free sort over absolute scores.

**Graph shape** (LangGraph enters at v3, when there are ≥4 components to coordinate):
`fetch → canonicalize → filter → extract → score → [HUMAN TRIAGE] → track → target → resolve ‖ select_variant → rank → [HUMAN] → draft ↔ critique → [HUMAN GATE] → send → close`

Three human interrupts, all durable. State checkpointed to Postgres.

---

## 5. GUARDRAILS

- **Prompt injection** — untrusted scraped pages + email tool access is the lethal trifecta. Untrusted content never shares context with tool-authorization decisions; mail parameters resolve outside the LLM path so a page cannot redirect a recipient; a poisoned-fixture test demonstrates both the exploit and the fix.
- **Fetch sandboxing** — domain allowlist, SSRF protection, redirect limits, size caps, timeouts.
- **Anti-spam** — daily and per-company send caps, dedupe preventing multi-board double contact, permanent no-auto-send.
- **Budget** — vendor call and model spend ceilings, hard stop rather than silent overspend.
- **Secrets** — public repo assumed; env-based secrets, pre-commit scanning from commit one.

---

## 6. BUILD ORDER

**v0 (weekend):** repo + tooling + `CLAUDE.md`; Postgres schema; constraints and applied-history seeded from real data; canonicalization + dedupe; hard-filter engine; extraction; CLI triage with persisted decisions and reason codes. Eval harness alongside, not after.

**v1:** experience atom corpus; fit scoring (deterministic + gap list); ranked shortlist; contact targeting rubric.
**v2:** resolver cascade T0–T2 + verification + confidence; resolver eval over golden set.
**v3:** drafter with citation map; critique loop; approval gate with durable interrupt; MCP mail tool.
**v4:** LangGraph orchestration; parallel fan-out; batch close + weekly report.
**v5+:** T3 vendor tier, preference model over decision history, similarity retrieval, graph traversal if data justifies.

**Permanently out:** automated application submission, auto-send, LinkedIn scraping that risks the account, a multi-user product version.

---

## 7. RESUME BULLETS

**Rule: no number goes on the resume until it is real and measured.** Bracketed values below are placeholders, not targets. A fabricated metric is the one unrecoverable interview failure — it invites exactly the follow-up question that exposes it.

### AI / Agentic resume — Job Sniper

▪ Built a stateful agentic job-search pipeline (Python, LangGraph, FastAPI, Postgres/pgvector) that canonicalizes postings across four feeds, filters against typed user constraints, and surfaces ranked roles — eliminating [X%] of duplicate and non-qualifying listings from a daily batch.

▪ Engineered a four-tier contact resolution service cascading cache → public-source extraction → email-pattern inference with MX verification → vendor API, with deterministically composed confidence scoring and first-class abstention; achieved [X%] hit rate at [X%] false-positive rate across [N] labeled records.

▪ Designed abstention as a correct output rather than a failure mode, on the reasoning that a plausible fabricated address fails silently on send — surfacing verified-only contacts and reporting abstention rate as a headline metric.

▪ Built an eval harness from the first commit — golden set, hit rate, precision/recall, abstention and false-positive tracking, model-swap regression — producing [N] months of longitudinal operating data as the system's daily user.

▪ Grounded all generated outreach in a retrieval corpus of atomic experience records with a citation map enforcing that every claim trace to a source record, structurally rejecting uncitable output.

▪ Threat-modeled prompt injection across untrusted scraped content feeding an agent with email tool access; isolated untrusted context from tool authorization, resolved mail parameters outside the model path, and wrote a poisoned-fixture test demonstrating both exploit and mitigation.

▪ Implemented durable human-in-the-loop gates with Postgres-checkpointed state, allowing multi-day pauses at approval steps to survive process restart; no message sends without explicit sign-off.

### SWE resume — same project, systems framing

▪ Built an asynchronous multi-stage pipeline with parallel fan-out and join, bounded retry loops, and checkpointed state persistence surviving process restart across multi-day workflow pauses.

▪ Designed entity canonicalization and deduplication across four heterogeneous data sources, normalizing inconsistent identifiers and titles into stable canonical keys — a correctness prerequisite for permanent exclusion state.

▪ Implemented a cost-bounded escalation strategy over external data providers, with per-tier budget metering, deterministic confidence composition, and verification gating before results are trusted.

▪ Modeled a normalized Postgres schema for a longitudinal decision and outcome record, supporting hit-rate-over-time and funnel conversion analysis.

### Notes on current resume text

The existing AI-resume bullets describe a supervisor-worker graph, pgvector retrieval, and an MCP-gated outbox in present progressive tense. Under this build order those arrive at v3–v4. Prepared answer if asked: *"I designed the orchestration graph first, then a week of live operation showed the bottleneck was stateful filtering and contact resolution, not orchestration — so I built and instrumented those first and deferred the graph until it had something to orchestrate."* That reordering is a stronger signal than having built the graph on schedule.
