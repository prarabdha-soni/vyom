# Vyom OS — Four Self-Contained Build Prompts

**Architecture direction:** Graph Safety–inspired patient-safety system design, using Google Cloud Vertex AI and Gemini behind the existing model-provider boundary.

**Important:** These are four separate, copy-paste-ready prompts. Run them in order. Each prompt contains the shared technical and safety constraints required to work independently. Do not begin a later milestone until the previous milestone's gate is satisfied. Milestone D is customer-driven and should only be started when a customer needs or funds the capability.

---

# PROMPT 1 OF 4 — Milestone A: Literature Pilot

## Role and objective

Act as the lead engineer working in the existing Vyom repositories, `vyom-os` and `vyom-web`. Take the current v2 foundation to a credible, secure, measurable literature-screening pilot for Indian generic pharmaceutical exporters. The commercial wedge is literature screening proven against each prospect's historical screening decisions—not a broad attempt to build every pharmacovigilance module at once.

Complete phases A0–A5 in the order below. Do not start implementation by rewriting the system. First inspect the existing repositories, current HLD/LLD, database schema, APIs, tests, deployment configuration, and product capability map.

## 1. Binding architecture decisions

These decisions apply throughout this prompt and supersede conflicting provider or architecture instructions in older documents.

### Preserve the current stack and infrastructure

- Keep `vyom-os` and `vyom-web` as the current application boundaries.
- Preserve the existing programming languages, frameworks, repositories, APIs, middleware, coding conventions, Docker/CI setup, deployment assumptions, hosting, queues, and infrastructure.
- Retain the existing Python/FastAPI service, PostgreSQL data layer, Next.js web application, and current infrastructure unless repository inspection demonstrates a concrete reason to change something.
- Do not migrate the database, hosting provider, queue, or deployment platform merely to imitate another vendor.
- Do not add a graph database, vector database, orchestration framework, or other dependency without documenting the need, trade-offs, operations impact, data-residency implications, and obtaining approval under the existing dependency rule.

### Vertex AI and Gemini

- Use Google Cloud Vertex AI as the managed AI service boundary and approved Gemini model APIs for appropriate model tasks.
- Add the Vertex AI/Gemini implementation behind the existing model-client/provider abstraction. Do not scatter Gemini SDK calls through FastAPI routes or domain logic.
- Use workload identity / Application Default Credentials or the deployment's approved identity mechanism. Never put service-account keys, API keys, or credentials in source, fixtures, screenshots, or logs.
- Configure and validate project, region, model ID, generation settings, timeout, retry policy, and supported safety settings. Pin model identifiers and record effective model/version metadata when available.
- Request structured outputs where supported and validate every output against application-owned schemas before it can influence routing or reach a reviewer.
- Treat model output as an untrusted proposal. A model must never write directly to the database, change tenant policy, approve a case, enable auto-close, or submit anything to a regulator.
- Use bounded timeouts and limited retries with backoff. Handle rate limits and provider errors explicitly. On timeout, malformed output, provider failure, or uncertainty, route to human review; never turn a provider failure into GREEN or auto-close.
- Record tenant, item, task, provider, model ID/version, prompt/schema versions, latency, available token usage, estimated cost, outcome, and correlation ID. Never log patient data or full source documents.
- Every material AI-generated assertion must be grounded in a stored source record and source span/offset where available. If evidence is insufficient, return `unknown` / `insufficient evidence` rather than inventing an answer.
- Keep provider-specific code separate from the domain model. Model selection must be configurable through versioned, auditable policy.

### System One / System Two operating model

Keep the existing pattern. These are workflow roles, not model vendor names:

- **System One:** fast, bounded classification and triage proposals with typed outputs.
- **Deterministic Python and SQL:** own thresholds, policy evaluation, routing, permissions, idempotency, and persistence.
- **System Two:** optional deeper drafting or summarisation for eligible items, with source references and human review. It may be asynchronous; System One remains synchronous.
- **Qualified humans:** own corrections, clinical/regulatory decisions, approvals, and authorized closure.

### Connected safety graph — without infrastructure rewrite

Adopt a provenance-first, Graph Safety–inspired logical evidence graph using the existing PostgreSQL infrastructure initially. Represent the minimum useful entities and typed relationships in tenant-scoped relational tables, reusing current tables where possible. Candidate entities include source records, literature, products, active ingredients, manufacturers, suppliers, batches, cases, institutions, regulatory alerts, evidence spans, model proposals, reviewer decisions, and audit events.

Every relationship must preserve tenant scope, source reference, provenance, creation time, and evidence status. Distinguish `verified`, `reported`, `inferred`, `unverified`, and `ruled_out`. Do not infer a batch match from a brand or ingredient match alone. Do not infer clinical causality from co-occurrence, geography, similar symptoms, or a shared investigation. Do not introduce a separate graph engine in this milestone unless an approved ADR demonstrates that it is necessary.

## 2. Non-negotiable rules

1. **Patient-data isolation:** Public literature (`pv_literature`) may use hosted System One processing under approved policy. Identifiable patient data (`pv_icsr`) remains local-only by default. Hosted processing of patient data is allowed only when the tenant contract explicitly permits it, the DPA/zero-retention terms and pinned region are configured, the policy is versioned, and the data-flow/security review has passed. If the policy is absent, ambiguous, or mismatched, fail closed. `hospital_rcm` remains frozen and local-only until separately decided.
2. **Append-only ledger:** Never update or delete a decision or human label. Corrections create a new row. Reject migrations that mutate historical decisions.
3. **Model pinning and reproducibility:** Every decision records `model_id`, `sampler_version`, `state_sha256`, `question_schema_version`, and `threshold_policy_version`. A decision must be replayable from its state hash and pinned versions.
4. **MedDRA boundary:** Preserve `event_verbatim` with character offsets into the source. Without the tenant's MedDRA licence, restrict coding to permitted public top-level SOCs. Licensed dictionary access is enabled per tenant, never globally.
5. **Control boundary:** System One proposes; deterministic code routes; System Two drafts; experts decide. No model writes to the database or submits to a regulator directly.
6. **Auto-close:** Off by default per tenant and item type. Enable only after measured recall meets the tenant's agreed threshold on adjudicated samples and a QPPV signs off through a recorded ledger decision. Continue a random human sample check (default 10%). Any error routes to a human.
7. **Numbers and sample records:** Every number in UI, docs, reports, or decks must be a sourced fact, a labelled target, or clearly marked sample data. Use fictional identifiers only in demos (for example `VY-201`, `VY-305`, `VY-412`, `VY-CASE-xxxx`, `Vendor A (FICTIONAL)`, `demo-hospital`, `demo-tpa`).
8. **Synthetic data only:** No real patient or customer data in repositories, tests, fixtures, demos, screenshots, or logs. Logs must not contain patient data or full article text.
9. **Context of use:** Every System One question has a versioned context-of-use record containing purpose, risk if wrong, evaluation method, and owner. Store it with `question_schema_version`. A question without this record cannot ship.
10. **Cost telemetry:** Every model call and OCR page records tenant, item, model ID, tokens/pages when available, and estimated cost. Mark unavailable values as unavailable; do not fabricate them.
11. **Tests:** Every phase ships tests. `vyom-os`: `pytest`. `vyom-web`: `npm run check`, plus existing build/test commands. No phase is complete with failing or silently skipped tests.
12. **Dependencies:** Ask for approval before adding a dependency.
13. **Accessibility and language:** Console work must target WCAG AA. Use Indian English in UI and docs (for example, “hospitalised”, “programme”, “licence”).
14. **Public historical data:** Clearly identify public-source examples as historical. Never present static records as a live feed or claim Vyom detected or prevented a historical incident. Keep public data separate from private hospital data.

## 3. Baseline to preserve

Inspect and verify the actual repository state before relying on this description. The documented v2 foundation includes System One routing, an append-only decision ledger, PubMed and Europe PMC literature sweep with deduplication, selective System Two drafting for Yellow/Red items, reviewer queue/action APIs, gold-set evaluation, and a training export path. Existing API surfaces include `/healthz`, `/v1/icsr/intake`, `/v1/literature/sweep`, `/v1/review/queue`, `/v1/review/states/{id}/actions`, `/v1/reports/gold/{version}`, and `/v1/reports/screening-log`. Do not assume functionality beyond what the code proves.

## 4. Implementation phases

### A0 — Harden what exists (no new product features)

- Load-test the literature sweep at 10x pilot volume. Use approximately 1,000 records/day/tenant as the pilot planning assumption and test 10,000/day. Run 50,000/day once as a stretch measurement, not a release gate.
- Record p50/p95/p99 latency for System One, dedup queries, and ledger inserts. Publish measurements, hardware, and test date in `vyom-os/docs/baseline-performance.md`.
- Add structured JSON logs with one event per decision and correlation IDs across ingest → System One → deterministic routing → System Two → queue. Do not log patient data or full article text.
- Extend `/healthz` to check database reachability, both System One endpoints, last successful sweep timestamp, and queue depth. Return 503 if a required dependency is unhealthy.
- Fail closed on System One timeout/5xx: route the item to human review. Add a test proving a System One failure cannot create GREEN or auto-close.
- Make a same-day sweep rerun idempotent: no duplicate `clinical_states` or decisions.
- Add cost telemetry per screened record, tenant, and week.
- Run the frozen gold set in CI on every prompt, model, or threshold change. Recall below the last released value fails the build; report precision changes. Never tune against the gold set.
- Fix skipped/flaky tests or document the reason for each remaining skip.

**A0 acceptance:** 10,000-record day completes without manual intervention and is measured; forced System One outage routes items to the queue; same-day rerun is a no-op; test-run cost per record is computed; deliberate recall regression fails CI; `pytest` is green with no unexplained skips.

### A1 — Tenancy and roles

- Add non-null UUID `tenant_id` to every data table; backfill existing rows to one bootstrap tenant. Add PostgreSQL row-level security so a tenant-scoped connection cannot read another tenant's rows. Service-role RLS bypass is allowed only in migrations and batch jobs, never request handling.
- Add a tenant table for slug, display name, residency region, MedDRA licence state, System One domain-routing policy, per-item-type auto-close policy, and feature flags.
- In FastAPI, resolve tenant from a validated JWT claim. `x-tenant-id` may route a request but must be cross-checked with the token; mismatch returns 403.
- Replace shared API/reviewer tokens with local accounts: hashed passwords, MFA, one account per person, and roles `reviewer`, `safety_physician`, `qppv`, `admin`, `ops`.
- Implement authorization as a policy table, not scattered `if` statements. A safety physician may approve; a reviewer may correct/escalate but cannot approve a serious case; only a QPPV may enable auto-close.
- Wire real sessions into `vyom-web` tenant routes and internal `/ops`. `/ops` is internal-only and returns 404 to tenant users.

**A1 acceptance:** database-level RLS test proves tenant A sees zero tenant B rows; forged tenant header with another tenant's valid token returns 403; every role/action allow and deny pair is tested; no shared credentials remain; `npm run check` and `pytest` pass.

### A2 — Literature completeness

- Implement versioned search strategies per tenant and molecule: substance name, synonyms, salts, brand names, and source-specific query. Every retrieved record stores the strategy version. Strategy changes are append-only and attributable.
- Implement a weekly scheduler per tenant with configurable day, catch-up for missed runs, and idempotent reruns. A missed run raises an alert. Use the existing PostgreSQL-backed queue pattern (`SELECT ... FOR UPDATE SKIP LOCKED`); do not add an orchestration dependency.
- Retain PubMed and Europe PMC. Add Embase only behind tenant-owned licence and credentials, isolated per tenant. Never use it without a licence.
- Allow per-tenant upload of digital local-journal PDFs/issues not indexed by PubMed. Extract text and retain page/character offsets. Scanned issues wait for the later OCR capability and must be labelled `manual review` rather than silently omitted.
- Use Europe PMC open-access full text; otherwise use full text only when the tenant supplies it under its own licence. Do not fetch from publisher sites.
- Deduplicate by PMID, then DOI, then title + first author + journal + year (fuzzy), and log the matching key.
- Add bounded System One questions for pregnancy/breastfeeding, paediatric/elderly use, overdose, abuse/misuse, off-label use, medication error, occupational exposure, and lack of efficacy.
- Keep EMA published substance and journal lists as versioned reference data. Flag matching records for reviewer attention; never make an automatic regulatory decision.
- Record awareness date when a record meeting the four minimum criteria (identifiable patient, reporter, suspect drug, event) is first seen by a screener. Store region/tenant rule and its version.
- Generate a screening log per run (retrieved, unique, screened, flagged, confirmed, by strategy/model version) and a case-ready draft for each confirmed case, with every field linked to a source span.

**A2 acceptance:** tenant-specific strategies for the same molecule remain isolated; missed weekly run alerts and catches up without duplicates; Embase is blocked without licence; uploaded digital PDF produces page offsets; run log reconstructs exact records and strategy/model versions.

### A3 — Literature reviewer console

- Read the existing `DESIGN.md` and use the existing design system. Implement a split-screen console at `/{tenant_slug}/console`: abstract/full text with highlighted evidence spans on the left; typed System One flags and calibrated probabilities on the right.
- Make it keyboard-first: J/K navigate, A approve, C correct, E escalate, `?` help. No action requires a mouse; maintain visible focus states.
- Inline corrections create a new append-only labels row with field-level diff. Never mutate the original decision.
- Display model ID, sampler version, and question schema version for the reviewed decision.
- Order the queue in SQL: escalations, likely valid cases, special situations, then oldest.
- Prevent two reviewers from receiving the same item using `SELECT ... FOR UPDATE SKIP LOCKED` and a lease timeout.
- Show sampled auto-closed items in the queue as explicit sample checks when a tenant has enabled auto-close.
- Measure time-to-decision per item and expose it on `/ops` by item type.

**A3 acceptance:** reviewer clears 50 sample items using keyboard only; real median time-to-decision is measured and shown (do not invent a target); concurrent sessions never get the same state; each action creates exactly one append-only labels row; design matches `DESIGN.md` at 1440px and has no horizontal scroll at 375/768px; `npm run check` passes.

### A4 — Benchmark runner

- Build an operator/CLI-first retrospective benchmark using a prospect's historical screening log: record IDs (PMID/DOI), screening date, prospect decision, whether a case was raised, and the search strategy for that period. Store it in a dedicated benchmark tenant.
- Re-run the same period with the prospect's strategy and pinned versions; compare decision by decision.
- Send disagreements to a qualified safety physician for adjudication. Store adjudication as an attributable ledger decision.
- If adjudication confirms a possible missed case (Vyom identifies a valid case the prospect's process did not raise), promptly notify the prospect's designated contact with evidence and record the notification.
- Produce recall and precision against adjudicated truth, all disagreements with evidence, reviewer time per record, and a methods section listing period, strategy, model versions, and adjudicator role.
- Support deletion of benchmark data on the agreed date through one command; retain a deletion record.
- Provide a CLI such as `vyom benchmark run --tenant <slug> --period <range>`. Do not build a self-serve UI in this milestone.

**A4 acceptance:** benchmark on public data with planted misses calculates recall/precision correctly and shows arithmetic in tests; benchmark tenant is isolated by RLS; confirmed possible missed case creates a notification record; deletion removes tenant data and leaves a deletion record.

### A5 — Pilot-grade operations

- Deploy `vyom-os` workers and managed PostgreSQL in an Indian region using the existing deployment pattern. Configure daily backups and point-in-time recovery if available.
- Rehearse one restore into a clean environment, time it, and document the procedure and result.
- Store secrets in a managed secret store. No deployed `.env` secrets and no secrets in the repository. Rotate any credential ever exposed in a chat or ticket. Add secret scanning to CI.
- Configure alerts that reach a named responsible person for failed/missed sweep, queue depth over threshold, and System One endpoint outage.
- Audit the website/product pages: every statement must map to a shipped capability or be labelled roadmap/design-partner. Do not claim that planned modules are live.

**A5 acceptance:** clean restore is timed and documented; forced sweep failure generates an alert; no repo secrets and secret scanner runs in CI; product-page claim audit is recorded.

## 5. Milestone A delivery order and gate

**Order:** A0 → A1; then A2 and A3 may proceed in parallel; then A4. A5 runs alongside A3/A4.

**Gate A — do not start Milestone B until:** all A-phase acceptance criteria pass; two paid pilots are signed; benchmark recall meets the agreed target on at least two prospects' data, adjudicated by a qualified safety physician.

**Out of scope for A:** new unrelated product modules, OCR for scanned literature (reserved for C1), serializers, OIDC/SSO, SCIM, billing, and broad redesign of infrastructure.

## 6. Required engineering workflow and final response

For each architecture-affecting change, inspect the current HLD/LLD first; update HLD component boundaries, data flows, trust boundaries, provider routing, tenancy, and failure paths; update LLD schemas, API contracts, state transitions, indexes, and tests; record decisions and rejected alternatives in an ADR. Implement the smallest change that meets acceptance. Add unit, integration, failure-mode, tenant-isolation, and regression tests. Run `pytest`, `npm run check`, and the repository's existing build/test commands. Update docs and capability map to distinguish shipped, planned, and demo-only features.

At completion, report changed files, tests and actual results, measurements, outstanding risks, and any capabilities still requiring real integrations. Do not claim an acceptance criterion passed unless it was tested.

---

# PROMPT 2 OF 4 — Milestone B: Production Literature + Audit

## Role and objective

Continue the existing Vyom repositories after Milestone A has passed Gate A. Turn the literature pilot into a production-grade contract and deliver **Vyom Audit**, a vendor-neutral quality-checking product for customer case data. Reuse the tenancy, roles, decision ledger, benchmark/recall gate, literature workflows, reviewer console, and pilot operations already delivered. Do not rebuild them.

This prompt covers B1–B4. B4 is conditional and should be implemented only when a customer requires enterprise identity.

## 1. Binding architecture and constraints

Preserve all architecture and safety decisions in Prompt 1:

- Existing `vyom-os` Python/FastAPI, PostgreSQL, `vyom-web` Next.js, Docker/CI, repositories, hosting, queue, infrastructure, APIs, coding languages, and conventions remain in place.
- Use Vertex AI as the managed AI boundary and Gemini through the existing provider adapter. No direct Gemini SDK calls in route handlers/domain code. Pin models and prompt/schema versions; validate structured outputs; use workload identity; log cost/latency/usage metadata without patient data or full source documents.
- Model output is a proposal. Deterministic Python/SQL controls rules, thresholds, permissions, routing, idempotency, and persistence. Human experts retain approvals and clinical/regulatory decisions.
- Keep the evidence graph logical and provenance-first in tenant-scoped PostgreSQL. No separate graph/vector database or workflow framework unless approved by ADR. Every edge has source provenance and verification status.
- Identifiable patient data stays local-only by default. Hosted processing is allowed only under explicit tenant contract, DPA/zero-retention conditions, approved region, versioned policy, and data-flow/security review. Ambiguity means fail closed. `hospital_rcm` remains frozen/local-only.
- Preserve append-only decisions/labels, model pinning and reproducibility, MedDRA licence boundaries, auto-close safeguards, synthetic-only tests/demos, context-of-use records, per-item cost telemetry, WCAG AA, Indian English, and dependency approval.
- Run `pytest`, `npm run check`, and existing build/test commands. No failing or silently skipped tests.

## 2. Starting context

Milestone A should have delivered tenant isolation/RLS, individual accounts/MFA/roles, literature strategies and scheduling, reviewer console, benchmark runner, append-only ledger, pilot deployment, backup/restore rehearsal, secret handling, alerts, and cost telemetry. Verify all of this in code and tests before proceeding. Do not assume an item shipped merely because it is described here.

## 3. Implementation phases

### B1 — Compliance evidence

- Build a reproducible inspection evidence pack. Given a case ID, run ID, or date range, produce a bundle containing every decision, model and prompt version, human action with actor/timestamp, strategy version, and original source document.
- Implement 21 CFR Part 11 alignment controls appropriate to the product: unique attributable identities from A1, meaning of signature recorded on approvals, documented time source, and retention policy enforced in code.
- Automate a release validation pack for model/prompt changes on a fixed release cadence (for example, quarterly). Each release includes locked model/prompt versions, frozen gold-set results, change log, and risk assessment so customer QA can review it.
- Generate IQ/OQ/PQ validation documentation from the test suite rather than maintaining disconnected manual documents.
- Implement a controlled auto-close enablement workflow. A QPPV reviews measured recall on adjudicated samples and enables auto-close for a specific item type through a signed, append-only ledger decision. Do not permit configuration-only or model-only activation.
- Add a CI rule that every System One question has a versioned context-of-use record with purpose, risk, evaluation method, and owner.

**B1 acceptance:** any case's inspection pack reconstructs full decision history including model and strategy versions; a release automatically creates its validation pack; auto-close cannot be enabled without recorded QPPV approval; a System One question lacking context-of-use fails CI.

### B2 — Vyom Audit mode

Build checks on 100% of customer-processed cases imported from their existing safety database. This milestone does not fix cases in the customer's system and does not submit them to regulators.

- Parse inbound E2B(R3) files into the existing clinical-state model and validate against the official schema. Quarantine invalid files with a readable error; never silently drop them.
- Implement a rules engine with versioned per-tenant rule data. Include coding-vs-narrative consistency, seriousness-vs-outcome, missing mandatory fields, duplicates, date logic, and late submission relative to the receipt date inside the file. Every finding records rule ID/version, evidence, and severity.
- Use System One only for questions deterministic rules cannot decide (for example, narrative mentions an event that is not coded). Treat its result as a proposal and send it through the normal human review flow.
- Produce a vendor scorecard per period: findings by type and rate, trends, and top findings. Add corrective-action export as CSV.
- Generate an evidence pack for each audit run using B1 machinery.
- Ensure MedDRA licensing is in place before Audit ships. Validate licence terms for processing customer-coded data. If required dictionary lookups are not permitted for a tenant, skip those checks and mark them clearly; do not return apparently complete results.

**B2 acceptance:** malformed E2B is quarantined with readable error; on 500 synthetic cases with seeded defects, report each rule's found/missed detection and publish measured results; scorecard for any past run is reproducible from the ledger; tenant without required MedDRA licence cannot receive dictionary-based checks.

### B3 — Production operations

- Enforce data residency per tenant, including the region in which the local System One worker runs. Treat this as a contractual control, not a UI preference.
- Add SLOs and alerting for intake availability, sweep completion, queue depth, and time-to-decision. Page a responsible operator on breach.
- Define documented recovery time and recovery point objectives. Rehearse and time a full restore every quarter.
- Expose per-tenant/per-item cost in `/ops` using A0 telemetry.
- Collect ISO 27001 control evidence from the system where possible: access reviews, change logs, backup tests, vulnerability scans, and related evidence. Do not claim certification merely because controls/evidence exist.
- Implement DPDP processor duties: retention limits, tenant data deletion on request, breach-notification procedure, and a record of processing per tenant.

**B3 acceptance:** SLO dashboard is live and a deliberate breach pages someone; quarterly restore rehearsal is recorded and timed; tenant data deletion completes and is logged; per-tenant/per-item cost is visible in `/ops`.

### B4 — Enterprise identity (only when required)

- Add OIDC against a customer's identity provider when configured; retain local accounts for tenants without OIDC.
- Map identity-provider groups to the existing Vyom roles without changing the A1 policy table.
- Make session and token lifetimes configurable per tenant.

**B4 acceptance:** end-to-end sign-in against a test identity provider works; existing A1 role-matrix tests pass unchanged for OIDC users.

**B4 out of scope:** SCIM provisioning and a dedicated SSO administration UI.

## 4. Milestone B delivery order and gate

Complete B1 before relying on its evidence-pack machinery in B2. B3 hardens the operational service. B4 is on-demand and may be deferred if no customer requires SSO.

**Gate B — do not start Milestone C until:** all required B-phase acceptance criteria pass; the first production contract is signed; the customer's QA accepts the validation pack; and an ISO 27001 certification audit is booked. Record any conditional B4 deferral and its customer rationale.

**Out of scope for B:** fixing imported cases inside the customer's system, regulatory gateway submission, broad multi-region active-active, SCIM, and unrelated platform rewrites.

## 5. Required engineering workflow and final response

Inspect current code, HLD/LLD, policies, and tests before each change. Update HLD trust boundaries, data flows, provider routing, residency and failure paths; update LLD schemas, rule versions, API contracts, validation states, indexes, and test cases; record material choices in ADRs. Use mocked Vertex responses in CI; live paid-model integration tests must be opt-in. Test malformed model output, timeout, rate limit, provider 5xx, empty/unsupported responses, and retry exhaustion. Prove provider failure cannot bypass validation, auto-close, approval, or tenant policy. Run frozen-gold-set evaluation for provider/model changes and block recall regressions.

At completion, report changed files, tests and real results, audit/validation artefacts generated, customer-dependent items, and any remaining production limitations. Do not imply ISO certification or regulatory compliance approval has been obtained unless it has.

---

# PROMPT 3 OF 4 — Milestone C: Pharmacovigilance Cases

## Role and objective

Continue from the existing Vyom production literature and Audit foundation after Gate B. Deliver the Cases product for a paying customer: multi-source intake, an evidence-linked case console, regulator-ready E2B(R3) export, and a regulatory clock with inline validation.

This milestone introduces patient-data workflows. Treat privacy, local/hosted processing policy, tenant isolation, expert approval, source provenance, and auditability as release-blocking requirements—not optional enhancements.

## 1. Binding architecture and constraints

- Preserve existing repositories, coding languages, Python/FastAPI and Next.js boundaries, PostgreSQL, hosting, queue, deployment, Docker/CI, APIs, HLD/LLD patterns, and coding conventions. No infrastructure rewrite to imitate another platform.
- Use Google Cloud Vertex AI and Gemini only behind the existing model-provider adapter. Pin model and prompt versions; use typed/validated structured outputs; use workload identity; bound timeouts/retries; record per-tenant/per-item cost and model metadata. Never log patient data or full source documents.
- Keep System One synchronous and bounded; deterministic code/SQL own all policy, thresholds, permissions, routing, idempotency, and persistence; System Two may draft asynchronously; qualified safety professionals own review and approval.
- Patient data remains local-only by default. Sending identifiable patient data to Vertex AI is prohibited unless the specific tenant contract explicitly permits it, DPA/zero-retention terms and approved region are configured, policy is versioned, and security/data-flow review passes. If any condition is absent or unclear, fail closed and keep processing local or route to human review. `hospital_rcm` remains frozen/local-only.
- Keep decisions and reviewer labels append-only. Corrections create new records. Preserve immutable originals and re-derivable extracted data.
- Maintain tenant-level RLS and prevent cross-tenant access through APIs, database queries, evidence links, and graph traversal.
- Use the existing PostgreSQL data layer for the logical evidence graph. Each product/batch/distribution/case relationship must carry tenant scope, provenance, timestamp, and verification status. Do not add a graph database or orchestration dependency without an approved ADR.
- Distinguish `verified`, `reported`, `inferred`, `unverified`, and `ruled_out`. Never infer batch identity from brand/ingredient alone or causality from co-occurrence, geography, similar symptoms, or shared investigation.
- Enforce MedDRA licensing per tenant. Retain verbatim terms and source offsets even when dictionary coding is unavailable.
- Auto-close is off by default. It requires measured recall, adjudicated samples, QPPV approval, append-only decision, and continued human sampling. Any processing error routes to human review.
- Use synthetic patient/case data only in tests, fixtures, demos, screenshots, and logs. Do not place real patient/customer data in repositories or test artefacts.
- Every System One question requires a context-of-use record. Every model field shown to a reviewer needs source provenance or an explicit unsupported-draft label.
- Accessibility target: WCAG AA. Use Indian English. Every phase must pass `pytest`, `npm run check`, and existing build/test commands.

## 2. Starting context

Verify that A and B are actually complete: tenant RLS and roles, append-only decision ledger, evidence pack, audit mode, production controls, and the current literature workflow. Verify current API contracts and HLD/LLD before implementation. Existing intake includes a structured `/v1/icsr/intake` endpoint and E2B(R3) inbound support from Audit; do not assume PDF/email extraction exists until code proves it.

## 3. Implementation phases

### C1 — Multi-source intake

- First create a synthetic corpus of 200 realistic fictional documents with known expected outputs: scanned PDFs, digital PDFs, email, E2B XML, call-centre notes, and other agreed source types. No real patient data.
- Implement PDF/text extraction. Parse digital PDFs directly; run OCR for scanned PDFs. Preserve character offsets and map every extracted field back to page and bounding box/region. Store original documents immutably; extracted text is derived and re-derivable. OCR stays inside the local patient-data path for `pv_icsr` under the tenant's processing policy.
- Implement per-tenant email intake with attachment extraction and thread deduplication. Store sender and received-at timestamp; this timestamp is relevant to regulatory clock logic in C4.
- Add a System One router with typed proposal for adverse event vs product complaint vs medical enquiry vs none-of-these. Deterministic application policy performs the actual routing.
- Deduplicate across sources: same case arriving via email and E2B must resolve to one `clinical_state` with both original `source_records` retained. Matching order: case identifier → patient + drug + event + date fuzzy match → content hash. Record which key matched and evidence for the match.
- Design the customer-facing intake endpoint once: `POST /v1/intake` accepts declared source type, returns a receipt ID immediately, and processes asynchronously. Define idempotency, auth, tenant resolution, status retrieval, errors, and retry semantics in HLD/LLD.
- Ensure a local-only tenant policy cannot reach a hosted model endpoint during intake. Add a network guard test proving the boundary.

**C1 acceptance:** all 200 synthetic documents ingest end to end without manual steps; every extracted field resolves to a page/region in the stored original (including scanned PDF); same case through email and E2B creates one clinical state and two source records; local-only policy makes zero hosted model requests; endpoint returns receipt ID and has tested idempotent retry/error behavior.

### C2 — Case console

- Extend the existing reviewer console to case documents. Show source PDF on the left and highlight the evidence span at its bounding box; show structured extracted fields, discrepancies, model suggestions, and source provenance on the right.
- Restrict serious-case approval to the `safety_physician` role defined in the A1 policy table. A standard reviewer can correct/escalate but cannot approve a serious case.
- Generate narrative drafts where every sentence links to a source span. A sentence without a source link blocks approval unless explicitly labelled as an unsupported draft and handled through the configured review policy.
- Order the queue in SQL: escalations, then serious cases, then soonest regulatory deadline, then oldest.
- Measure case time-to-decision separately from literature items and expose the actual measured result in `/ops`.
- Preserve keyboard-first interaction, visible focus, accessible source highlighting, and reviewer locking/lease semantics from A3.

**C2 acceptance:** reviewer cannot approve a serious case; narrative sentence without source blocks approval; case time-to-decision is measured and visible in `/ops`; 50 synthetic cases can be processed keyboard-only; concurrency and audit actions are tested.

### C3 — Regulatory output (export only)

- Implement an E2B(R3) serializer from approved `clinical_state` and decisions to valid R3 XML. Validate against the official schema in CI, not only at runtime.
- Implement regional profiles for EMA, FDA, and CDSCO as versioned data/configuration rather than hard-coded code branches. Profile changes should be data changes where possible.
- Implement MedDRA coding behind the tenant licence boundary. With a valid tenant licence, map `event_verbatim` to LLT/PT and record dictionary version. Without a licence, emit verbatim term and permitted SOC information only, and mark the export as requiring coding before submission.
- Provide export for import into the customer's existing safety database. Add an append-only export ledger with payload hash, profile version, timestamp, operator, and outcome.
- Produce aggregate data exports such as line listings and summary tabulations as data first; formatted PSUR documents are not part of this phase.
- Do not transmit to regulators in C3. Gateway submission belongs to D1.

**C3 acceptance:** generated R3 XML validates against official schema in CI; regional profile change can be made as data change and is tested; tenant without MedDRA licence cannot emit coded terms; export ledger reconstructs full export history of a case.

### C4 — Regulatory clock and inline validation

- Implement day-zero determination per case, region, and seriousness. Support 15-day and 90-day reporting tracks as configured by the applicable regional policy. Day-zero is a provenance-bearing decision, not an invisible derived timestamp.
- Alert before a deadline breach and record every breach with its cause, source facts, and decision history.
- Run the B2 validation rules continuously during case processing, not only at the end. Surface new findings in the case console as they occur; preserve rule ID/version, evidence, severity, and resolution state.

**C4 acceptance:** clock works across configured regions and seriousness levels; test edge cases including weekend day-zero, follow-up information, and retrospective information; inline findings appear before approval; deliberate near-breach raises an alert.

## 4. Milestone C gate

**Gate C — do not start Milestone D until:** all C-phase acceptance criteria pass; the first Cases customer is live; hosted-vs-local patient-data processing terms are explicitly written into that customer's contract; and the operational team can demonstrate end-to-end evidence traceability and reviewer approval controls.

**Out of scope for C:** regulator gateway transmission/ACK handling (D1), signal detection (D2), self-serve commercial onboarding (D3), and unsupported automated causality decisions.

## 5. Required engineering workflow and final response

Before implementation, inspect the current code, HLD/LLD, tenant policy and API contracts. Update HLD data-flow/trust-boundary diagrams for document ingestion, OCR, email, model routing, local-vs-hosted paths, and regulator export. Update LLD schemas, source-offset representation, API contracts, dedup keys, workflow states, regulatory clocks, indexes, and test cases. Record architectural decisions and rejected alternatives in ADRs. Use mocked Vertex responses in CI and opt-in integration tests only. Test timeouts, malformed output, provider 5xx/rate limits, network-policy denial, duplicate intake, tenant isolation, and reviewer permission boundaries.

At completion, report changed files, tests and actual results, supported intake sources, export profiles, regulatory clock assumptions, data-flow/security review status, and any features still requiring customer contracts, licences, or external integrations. Do not describe a draft or static demo as a production integration.

---

# PROMPT 4 OF 4 — Milestone D: On-Demand Capabilities

## Role and objective

Continue the production Vyom platform only when a paying customer needs or funds a specific capability. This milestone contains three deliberately deferred capabilities: regulator gateway submission, signal detection, and self-serve commercial workflows. Do not start all three by default. Confirm the customer requirement, contract, data permissions, regulatory responsibilities, and commercial case before selecting a phase.

## 1. Binding architecture and constraints

- Preserve the established `vyom-os` / `vyom-web` architecture, languages, APIs, HLD/LLD conventions, PostgreSQL data layer, current infrastructure, queues, deployment, Docker/CI, and provider abstraction. Do not rewrite or migrate the stack to imitate a competitor.
- Use Vertex AI and Gemini through the existing provider adapter only. Pin model/prompt/schema versions, validate structured outputs, apply bounded timeouts/retries, record per-item/per-tenant cost and model metadata, and keep all provider calls subject to tenant policy.
- System One proposes; deterministic code/SQL owns policies, thresholds, routing, permissions, idempotency, and state transitions; System Two may draft; qualified humans approve clinical and regulatory actions. A model must never submit to a regulator or close an item.
- Patient data remains local-only by default. Any hosted processing must be explicitly permitted by the tenant contract and versioned policy, with DPA/zero-retention terms, approved region, and completed security/data-flow review. Ambiguous policy fails closed. `hospital_rcm` remains frozen/local-only.
- Preserve tenant RLS, append-only decision/export/submission/evaluation ledgers, model pinning, provenance, MedDRA licence boundaries, auto-close restrictions, synthetic-only test data, context-of-use records, and cost telemetry.
- Keep the evidence graph logical and provenance-first in PostgreSQL unless a separately approved ADR justifies a different store. Every edge has tenant scope, source, timestamp, and evidence status. Never equate shared product names or similar reports with a confirmed batch or causal relationship.
- Keep the frozen gold set separate from the correction pool. Do not tune against the gold set. No real patient or customer data in tests, fixtures, logs, screenshots, or benchmark artefacts.
- Maintain WCAG AA, keyboard accessibility, and Indian English. Run `pytest`, `npm run check`, and existing build/test commands.

## 2. Starting context

Verify Milestones A–C are complete and their gates passed. In particular, verify working production tenancy, audit trail, validated E2B(R3) export, case console, source evidence, regulatory clock, and customer data-processing policy. Confirm actual implementation state; do not treat a roadmap label as a shipped feature.

## 3. Customer-triggered phases

### D1 — Regulatory gateway submission

Build only under a customer contract that explicitly makes Vyom responsible for regulator submission. This expands validation, operational and legal responsibility.

- Integrate with the relevant regulator test gateway using approved credentials and documented endpoint/version configuration.
- Implement submission transmission and acknowledgement handling. Store and reconcile ACK1/ACK2 where the gateway protocol uses them. Surface failures and acknowledgement mismatches in the console.
- A transmission with no recorded/reconciled acknowledgement is not complete and must not display as `submitted`. Use explicit states such as queued, transmitted, awaiting acknowledgement, acknowledged, rejected, retryable failure, and manual investigation as appropriate to the actual gateway contract.
- Maintain an append-only submission ledger for every attempt: payload hash, endpoint, timestamp, operator/service identity, correlation ID, response/acknowledgement reference, and outcome. Never overwrite prior attempts.
- Apply idempotency and safe retry rules so a transient failure cannot create duplicate regulator submissions. Document reconciliation and manual recovery procedures.
- Keep regulator onboarding paperwork and customer/QA responsibilities distinct from software implementation.

**D1 acceptance:** complete round trip against a regulator test gateway; acknowledgements stored and reconciled; missing ACK cannot show submitted; append-only ledger reconstructs every attempt and case history; duplicate-submission and retry behavior are tested.

### D2 — Signal detection

Build this last among the D capabilities. Do not develop signal detection over incomplete or poorly calibrated case data. Confirm completeness and the customer's need before starting.

- Aggregate safety cases across products, sources, and time with strict tenant scoping.
- Implement disproportionality statistics such as PRR and ROR with confidence intervals. Calculate on tenant data and public FAERS data separately; never silently pool the two populations or mix their denominators.
- Store thresholds as versioned per-tenant policy with append-only decision history.
- Turn every threshold crossing into a tracked evaluation item with an owner. It must close with a decision record explaining evidence, findings, decision, reviewer, and rationale—never silently close.
- Route relevant literature alerts into the same evaluation workflow.
- Build the Signal console by reusing existing A3/C2 reviewer and evidence primitives.
- Present statistical associations as signals for expert assessment, not proof of causality. Do not automate causality assessment or produce unsupported regulatory conclusions.

**D2 acceptance:** PRR/ROR values and confidence intervals match a worked reference example, with arithmetic shown in tests; tenant data and FAERS are never combined in one statistic; every evaluation closes with a decision record; thresholds are versioned and auditable; signal outputs link to the underlying cases and sources.

### D3 — Self-serve commercial surface

Extend the operator-run A4 benchmark into a controlled prospect/customer workflow while retaining its safeguards.

- Allow a prospect to upload a historical sample and receive recall/precision results on its own data. Preserve adjudication, notification of possible missed cases, tenant isolation, agreed retention, and deletion/audit logging.
- Implement tenant onboarding: provision tenant, configure strategies and thresholds, and import historical data through authorized workflows.
- Add in-product reporting for weekly screening log, recall report, and vendor scorecard.
- Export usage and billing data per the approved per-item pricing model. This phase does not include payment processing or contract management.
- Make the process understandable without an engineer, with validation, progress states, readable errors, retry handling, and clear data-retention/deletion terms.
- Ensure all reported metrics come from real executed benchmarks and are accompanied by methods/version information. Never invent performance numbers.

**D3 acceptance:** prospect completes a benchmark without engineer intervention; uploaded data stays tenant-isolated and is deleted/logged under the agreed policy; every product-page claim maps to a shipped capability; `npm run check` passes and every number is sourced, a labelled target, or clearly marked sample data.

## 4. Sequencing and commercial gate

- **D1:** start only when a customer contract requires Vyom to submit on its behalf and regulator test access is available.
- **D2:** start only when the underlying case data is sufficiently complete and calibrated and a customer funds/requires signal workflows. Keep it last because incomplete case data can produce misleading signals.
- **D3:** start when self-serve onboarding/benchmarking is a demonstrated sales or operational bottleneck.

There is no blanket D milestone gate that requires all three capabilities. Each phase has its own customer trigger, acceptance criteria, approved scope, and release decision. Do not build an on-demand capability merely because it appears in the roadmap.

## 5. Required engineering workflow and final response

For the selected D phase, inspect the existing implementation and customer requirement first. Update HLD/LLD for trust boundaries, regulator integration, statistical methodology, data lifecycle, idempotency, failure/reconciliation paths, API contracts, schemas, state machines, and indexes. Document choices and rejected alternatives in ADRs. Use test gateways and synthetic datasets; do not use real patient/customer data in tests or logs. Mock Vertex calls in CI; paid integration checks are opt-in. Test provider and gateway failures, timeouts, duplicate attempts, invalid acknowledgements, tenant isolation, statistical arithmetic, and audit reconstruction as applicable.

At completion, report which customer-triggered phase was implemented and why, changed files, tests and actual results, external dependencies/credentials/licences, operational runbooks, and remaining gaps. Clearly label capabilities not implemented. Do not claim a regulator submission, safety signal, or self-serve workflow is live until it has passed its specific acceptance criteria.

---

# Shared release checklist for all four prompts

Before marking any phase complete:

- [ ] Existing code, architecture, HLD/LLD, and APIs were inspected before changes.
- [ ] Existing languages, infrastructure, repositories, deployment assumptions, and coding patterns were preserved unless an approved ADR says otherwise.
- [ ] Vertex AI/Gemini is accessed only through the provider adapter; model/prompt/schema versions are pinned and recorded.
- [ ] No patient data can reach a hosted model without explicit tenant contract, configured policy, approved region/terms, and security review.
- [ ] Tenant isolation is enforced at database and service layers.
- [ ] Decisions, labels, exports, and submissions are append-only; corrections create new records.
- [ ] Material AI assertions link to source records/spans or are clearly labelled unsupported drafts.
- [ ] Model/provider failures fail closed and cannot bypass validation, tenant policy, or human approval.
- [ ] No graph relationship is represented as verified without supporting evidence; no batch or causality inference is fabricated.
- [ ] Tests use synthetic data only; logs contain no patient data or full source documents.
- [ ] Per-item/per-tenant model and OCR cost telemetry is present or explicitly marked unavailable.
- [ ] `pytest`, `npm run check`, and the existing build/test commands pass.
- [ ] HLD/LLD, ADRs, operational documentation, and the capability map are updated.
- [ ] Shipped, planned, and demo-only capabilities are clearly distinguished.
- [ ] Final report contains actual test results and does not claim unverified functionality.
