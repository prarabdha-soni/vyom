# Agent prompt — multi-channel PV intake pipeline on Vyom OS

> **How to use:** paste this entire file into your coding agent as its task, with
> the repository root as the working directory. It is written *to the agent*.
> The agent works milestone by milestone and stops after each one to report.
> Nothing here requires an API key, a paid service or real patient data.

---

## 0. Mission

Turn `vyom-os` from a literature-screening engine into a **multi-channel
pharmacovigilance intake pipeline**: safety-mailbox emails, social-media posts,
web forms, call-centre transcripts and literature go in; triaged,
de-duplicated, graph-linked, clocked, reviewable safety records come out.

It must **run end to end on synthetic data with one command (`make demo`),
offline, with no API keys**, and every step must land on the existing
append-only ledger.

When you are done, `make demo` turns the 15 fictional inputs in §8 into:

| Outcome | Count |
| --- | --- |
| Safety cases (`VY-CASE-0001` … `0007`) | 7 — six on a submission clock, one pregnancy exposure on follow-up only |
| Product complaints | 2 — both on batch `VYB-0042`, linked in the graph |
| Medical-information enquiries | 1 |
| Literature referrals (news shared on social) | 1 |
| Auto-closed | 2 — one spam post, one animal study |
| Not auto-closed although the system thinks it is noise | 1 — because it names a product |
| Follow-up linked to an existing case | 1 — via email threading |
| Duplicate merged into an existing case | 1 — a web form repeating an email |

---

## 1. Read these first

1. `CLAUDE.md` — repository rules. Content rules 1–9 apply to fixtures too.
2. `system-design.md` — the target architecture and its vocabulary
   (System One / System Two, bands, the decision ledger).
3. `vyom-os/README.md` — what v2 has and does not have.
4. `vyom-os-build-prompts.md` — the phase plan and the **pharmacovigilance-only
   scope note**. Hospital RCM is deferred, not deleted.
5. Code: `vyom-os/src/vyom_literature/system_one.py`, `ledger.py`,
   `ingestion.py`, `api.py`, `review.py`, `system_two.py`, `records.py`,
   `dedup.py`, and `vyom-os/migrations/002_*.sql`, `003_*.sql`.

What already exists and **must be reused, not rebuilt**:

- `SystemOneRouter.evaluate(domain, normalized_state)` with domain-keyed client
  selection: `pv_literature` → hosted client; `pv_icsr` and `hospital_rcm` →
  local client. Tested in `tests/test_system_one.py`.
- The `SystemOneClient` protocol — tests already use fakes against it.
- Ledger tables `source_records`, `clinical_states`, `sys1_decisions`,
  `sys2_syntheses`, `human_labels`, with **database triggers that reject
  UPDATE and DELETE**.
- `record_state_and_source`, `append_sys1_decision`, `append_sys2_synthesis`.
- A unique index on `sys1_decisions (state_id, model_id, sampler_version,
  question_schema_version, threshold_policy_version)` — idempotency is already
  structural. Keep it that way.
- `POST /v1/icsr/intake` — but it accepts an **already-normalised** state.
  There is no parser for a raw email, a social post, a form or a transcript.
  That gap is this task.

---

## 2. The benchmark, and what "like it" can honestly mean

The reference is graphsafety.ai. As of 2026-10-31 its site states:

| Item | What it publicly states |
| --- | --- |
| Modules | `/intake`, `/nucleus`, `/report` — available. `/signal` — Q1 '27. `/assure`, `/comply` — Q2 '27 |
| Model platform | "Vertex AI for medical reasoning" |
| Orchestration | "Kubernetes-native orchestration" |
| Data model | "a unified knowledge graph" |
| Human control | "review, validation, and override at every step" |
| Named sources | Literature; patient-support programmes |
| **Not stated** | Email, social media, call centre, which database, which graph store, which models |

So "exactly like it" can only mean four things, and this task does all four:
**modular intake → case-building → reporting**, **a knowledge graph linking
case evidence**, **Kubernetes-native deployment**, and **expert-in-the-loop on
every decision**. Everything else here is our own design.

**Email and social-media intake are our addition, not something the benchmark
claims.** That is fine — it is what our buyers' mailboxes and brand-monitoring
teams actually produce — but do not describe it as matching them.

**Never name the benchmark company in code, comments, commit messages, UI copy
or `src/content/`.** It may appear in this file only.

---

## 3. Non-negotiables

Copy this block into any sub-task you spawn.

```
1. PHI BOUNDARY IS DOMAIN-KEYED, AND PUBLIC IS NOT NON-PERSONAL.
   Literature -> pv_literature (hosted model allowed).
   Email, web form, social post, call transcript, partner E2B -> pv_icsr
   (local model only). A public tweet about someone's vomiting is health
   data about an identifiable person. It never reaches a hosted endpoint.
   Adding a provider never changes which domains may leave the local boundary.

2. APPEND-ONLY EVIDENCE. Never UPDATE or DELETE source_records,
   clinical_states, sys1_decisions, sys2_syntheses, human_labels, or any new
   evidence table you add. Never disable or drop the triggers. Corrections
   are new rows. (The job queue in §5 is operational state, not evidence,
   and is allowed to be mutable.)

3. THE MODEL PROPOSES, CODE DECIDES. Providers return probabilities.
   Deterministic Python owns every threshold, every workflow, every band and
   every link. No provider output is ever a verdict on its own.

4. ONE AUTONOMOUS PATH. The only thing the system may do without a human is
   GREEN_CLOSE, and only through the gate in §7. Everything else reaches a
   person. When anything fails, fail toward a human, never toward a closure.

5. NO OUTBOUND CONTACT. The system never replies to an email, never sends a
   DM, never posts. It drafts follow-up questions; a person sends them.

6. REPRODUCIBLE. Every decision records model_id, sampler_version,
   question_schema_version, threshold_policy_version and state_sha256 over a
   canonically serialised state. Never call datetime.now() inside pipeline
   logic — inject a clock. The demo runs at a fixed "now".

7. FICTIONAL DATA ONLY. Drug codes VY-201, VY-305, VY-412. Case ids
   VY-CASE-xxxx. People and organisations end in "(FICTIONAL)". Email domains
   use the reserved .example TLD. Never copy a real post, email, person or
   handle into a fixture.

8. MedDRA LICENCE BOUNDARY. Store event_verbatim exactly as written, with
   character offsets into the stored text. No MedDRA coding.

9. DEMO RESULTS ARE NOT EVIDENCE. The demo provider is a keyword stub written
   against these fixtures, so its "accuracy" is circular. Never report demo
   recall or precision anywhere, as anything.

10. DO NOT: rename the vyom_literature package; delete or alter RCM code
    (hospital_rcm, /v1/rcm/preflight, cpc_coder, tpa_auditor); touch
    vyom-web, CLAUDE.md or DESIGN.md (unless §9 M9 is approved); add a
    dependency without asking; commit a secret or print one.
```

---

## 4. Target architecture

### 4.1 Flow

```
 channels                 intake                    nucleus                  assure / comply          report
 ────────                 ──────                    ───────                  ───────────────          ──────
 email (.eml)   ─┐
 social (JSON)  ─┤   parse → store raw   ─►  deterministic links      ─►  inline checks        ─►  reviewer
 web form       ─┼─► (source_records,        (email thread, hash)          (assure_findings)        ACCEPT
 call transcript─┤    append-only)                 │                            │                     │
 literature     ─┘         │                       ▼                            ▼                     ▼
                           ▼                 System One (demo |         provisional day zero    E2B(R3)-shaped
                     normalise + redact      local | hosted*)           + due dates             DRAFT export
                     + deterministic         → workflow + band          (case_clock_events)
                       pre-checks                  │
                       (catalogue, dates)          ▼
                                             fuzzy duplicate link
                                             → case assembly (graph)
                                                   │
                                                   ▼
                                             System Two draft
                                             (YELLOW/RED safety cases;
                                              follow-up questions)

 * hosted only for pv_literature
```

### 4.2 Four dimensions — never let one stand in for another

| Dimension | Values | Governs |
| --- | --- | --- |
| **channel** — where it came from | `safety_email`, `web_form`, `social_post`, `call_transcript`, `partner_e2b`, `literature` | Parser, dedup keys, day-zero basis |
| **domain** — what class of data it is | `pv_literature`, `pv_icsr` (`hospital_rcm` untouched) | Which model endpoint may see it, which question set |
| **workflow** — which team must act (multi-valued) | `safety_case`, `product_complaint`, `medical_information`, `literature_referral`, `not_safety_relevant` | Queues |
| **band** — how much autonomy | `GREEN_CLOSE`, `YELLOW_REVIEW`, `RED_ESCALATE` (`GREEN_PASS` stays RCM-only) | Whether a human must act, and how urgently |

Do not route PHI by channel. Do not infer urgency from workflow. Do not let a
workflow label close anything.

### 4.3 Modular monolith, not microservices

Mirror the benchmark's module boundaries as **subpackages in one codebase,
deployable as several processes from one image**. Do not split into separate
services or repositories — that is premature at this scale and would turn
every change into a coordinated deploy.

```
vyom-os/src/vyom_literature/
  channels/        email.py  social.py  web_form.py  call_transcript.py  literature.py
  intake/          normalise.py  redact.py  pseudonymise.py  precheck.py
  nucleus/         graph.py  link.py  cases.py
  assure/          checks.py
  comply/          clock.py  audit_pack.py
  report/          e2b_draft.py
  providers/       demo_sys1.py  demo_sys2.py
  pipeline/        jobs.py  stages.py  worker.py
  demo/            cli.py
```

Entry points (add to `pyproject.toml`): `vyom-worker`, `vyom-demo`. Keep the
existing ones working.

---

## 5. Data model — `migrations/004_multichannel_pipeline.sql`

**Additive only.** No change to an existing row. Existing check constraints may
be widened (drop and recreate the constraint) — that alters no data.

1. **Widen `source_records.source`** to add `web_form` and `social_post`.
   `safety_email` and `call_transcript` already exist. Map channel `literature`
   to the existing `pubmed` / `europepmc` values. **Do not create a second raw
   store** — raw input lives once, in `source_records`, under its trigger.

2. **`sys1_decisions.workflows text[]`**, nullable (null on historical rows =
   literature workflow), with a check that every element is in the §4.2 list.

3. **Graph** — a linkage index over the ledger. Facts stay in the ledger;
   the graph records how they connect.

   ```sql
   graph_nodes (
     id           bigserial primary key,
     kind         text not null check (kind in
                    ('case','source_document','reporter','product','event_verbatim','batch')),
     natural_key  text not null,
     created_at   timestamptz not null default now(),
     unique (kind, natural_key)
   )
   graph_edges (
     id                 bigserial primary key,
     src_node_id        bigint not null references graph_nodes(id),
     dst_node_id        bigint not null references graph_nodes(id),
     kind               text not null check (kind in
                          ('derived_from','follow_up_of','duplicate_of','possible_duplicate_of',
                           'reported_by','mentions_product','reports_event','mentions_batch')),
     role               text,                 -- e.g. 'suspect' | 'concomitant' on mentions_product
     evidence           jsonb not null,       -- method, score, rule_version, matched fields
     decided_by         text not null,        -- 'system' or a reviewer uuid
     retracts_edge_id   bigint references graph_edges(id),
     created_at         timestamptz not null default now()
   )
   ```
   `evidence.method` is one of `deterministic_thread`, `deterministic_hash`,
   `fuzzy_fingerprint`, `model`, `human`. A correction is a new edge with
   `retracts_edge_id` set. Both tables append-only, with the same trigger.

4. **`assure_findings`** — `state_id`, `case_node_id`, `code`, `severity`,
   `detail jsonb`, `rule_version`, `created_at`. Append-only.

5. **`case_clock_events`** — `case_node_id`, `event`
   (`day_zero_provisional`, `day_zero_confirmed`, `due_date_set`,
   `follow_up_due_set`, `no_submission_clock`, `breached`), `at`,
   `basis jsonb`, `policy_version`, `created_at`. Append-only.

6. **`report_drafts`** — `case_node_id`, `format` (`e2b_r3_draft`),
   `payload_sha256`, `body text`, `created_at`. Append-only.

7. **`pipeline_jobs`** — **operational, mutable, no trigger.**
   `id`, `stage`, `subject_id`, `domain`, `status`
   (`queued|running|done|failed|dead`), `attempts`, `available_at`,
   `locked_until`, `last_error`, `created_at`, `updated_at`,
   `unique (stage, subject_id)`.
   Workers claim with `SELECT … FOR UPDATE SKIP LOCKED` and a lease. Write a
   comment in the migration explaining why this table alone is mutable.

8. Indexes for: queue claim (`status, stage, domain, available_at`), edge
   traversal (`src_node_id, kind`), (`dst_node_id, kind`), clock lookups.

---

## 6. Channels, normalisation and redaction

### 6.1 Adapters

Each adapter turns one raw input into a `ChannelMessage` (your dataclass) and
stores the raw bytes/JSON once in `source_records`. **Use the Python standard
library only** — `email.parser.BytesParser(policy=email.policy.default)` for
`.eml`, `json` for the rest. No new dependency for parsing.

| Channel | Demo input | Real-world connector (not built here) | Day-zero basis |
| --- | --- | --- | --- |
| `safety_email` | `.eml` files (RFC 5322) | IMAP or Microsoft Graph / Gmail API mailbox poller | `Date` header received time |
| `web_form` | JSON | HTTPS POST from the public form | `submitted_at` |
| `social_post` | JSON shaped like the X API v2 tweet object, plus a `_vyom` envelope we add | Platform API poller, **only after legal review** (Appendix A) | `_vyom.detected_at` — when **we** became aware, not when it was posted |
| `call_transcript` | Plain text with a header block | Call-centre platform export | `RECEIVED` header |
| `literature` | JSON shaped as `LiteratureRecord` | Existing PubMed / Europe PMC sweep | ingest time |

Email specifics: keep `Message-ID`, `In-Reply-To` and `References` (hashed) for
threading. Strip quoted reply text (`>` lines and "On … wrote:" blocks) from the
text used for evaluation and fuzzy matching, but keep it in the raw record.
Attachments: record filename, MIME type and sha256; do not process them (OCR is
a later phase) and add an `ATTACHMENT_NOT_PROCESSED` finding.

### 6.2 Normalised state — one canonical shape

```json
{
  "schema": "vyom.normalized_state/1",
  "channel": "safety_email",
  "domain": "pv_icsr",
  "received_at": "2026-10-26T09:14:00+05:30",
  "detected_at": "2026-10-26T09:14:00+05:30",
  "reporter": { "key": "rep_…", "qualification_hint": "healthcare_professional" },
  "text": "…redacted evaluation text…",
  "segments": [ { "kind": "subject", "start": 0, "end": 37 }, { "kind": "body", "start": 38, "end": 612 } ],
  "precheck": {
    "catalogue_matches": [ { "product": "VY-201", "surface": "VY-201", "start": 120, "end": 126 } ],
    "batches": [],
    "dates": [ { "surface": "20 Oct 2026", "iso": "2026-10-20", "start": 140, "end": 151 } ]
  },
  "thread": { "message_id_hash": "…", "in_reply_to_hash": null }
}
```

- **Redaction before the model sees anything:** email addresses, phone numbers
  and social handles become `[EMAIL_1]`, `[PHONE_1]`, `[HANDLE_1]`. All offsets
  refer to the redacted text. Raw stays in `source_records`. Personal names are
  **not** reliably redacted by regex — record that as a known gap (it needs an
  NER step later); pv_icsr only ever goes to the local model, so this is
  tolerable for now, not solved.
- **Pseudonymisation:** reporter key = `HMAC-SHA256(PSEUDONYM_SALT,
  normalised identifier)` — lower-cased email, or `platform:username`. The demo
  uses a fixed, clearly-labelled demo salt.
- **Deterministic pre-check:** product catalogue match with the regex
  `\bvy[\s-]?(201|305|412)\b`, case-insensitive (so `VY-201`, `vy 201`,
  `vy305` all match). Batch numbers `\bVYB-\d{4}\b`. Date parsing for the
  formats in the fixtures.
- **Canonical serialisation** for `state_sha256`: the existing
  `json.dumps(…, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`.
  Do not invent a second one.

---

## 7. System One questions and routing policy

### 7.1 Versions become per-domain

```python
QUESTION_SCHEMA_VERSIONS  = {"pv_literature": 2, "pv_icsr": 3, "hospital_rcm": 2}
THRESHOLD_POLICY_VERSIONS = {"pv_literature": 4, "pv_icsr": 5, "hospital_rcm": 4}
```

**`pv_literature` and `hospital_rcm` behaviour must be byte-identical to
today.** If an existing test asserts a module-level version constant, keep that
constant as an alias for the literature value and extend the tests — never
weaken an existing assertion.

### 7.2 New `pv_icsr` questions (schema v3)

Keep every existing `PV_ICSRS_QUESTIONS` entry. Add:

| Key | Kind | Values / meaning |
| --- | --- | --- |
| `report_type` | choice | `ADVERSE_EVENT`, `SPECIAL_SITUATION`, `PRODUCT_COMPLAINT`, `MEDICAL_INQUIRY`, `NOT_SAFETY_RELEVANT`, `UNCERTAIN` |
| `post_nature` | choice | `FIRST_PERSON_EXPERIENCE`, `ABOUT_ANOTHER_PERSON`, `NEWS_OR_ARTICLE_SHARE`, `PROMOTIONAL_OR_SPAM`, `HUMOUR_OR_HYPERBOLE`, `NOT_APPLICABLE`, `UNCERTAIN` |
| `has_quality_defect` | noul | A product quality defect is described |
| `special_pregnancy_exposure` | noul | |
| `special_overdose` | noul | |
| `special_misuse_or_abuse` | noul | |
| `special_medication_error` | noul | |
| `special_lack_of_efficacy` | noul | |
| `special_off_label_use` | noul | |

The four validity gates are about **a human case**: score `has_suspect_drug`
low when there is no human subject (an animal study gives a drug to rats; that
is not a suspect drug in a human case).

### 7.3 Routing policy v5 (`pv_icsr`) — implement exactly

```python
workflows = set()
if (report_type in {"ADVERSE_EVENT", "SPECIAL_SITUATION"}
        or (p_event >= 0.10 and p_patient >= 0.10)
        or any(p >= 0.50 for p in special_situation_probabilities)):
    workflows.add("safety_case")
if report_type == "PRODUCT_COMPLAINT" or p_quality_defect >= 0.50:
    workflows.add("product_complaint")          # never suppresses safety_case
if report_type == "MEDICAL_INQUIRY":
    workflows.add("medical_information")
if channel == "social_post" and post_nature == "NEWS_OR_ARTICLE_SHARE":
    workflows.add("literature_referral")
if not workflows:
    workflows.add("not_safety_relevant")

if "safety_case" in workflows and (p_serious >= 0.50 or priority >= 4):
    band = "RED_ESCALATE"
elif (workflows == {"not_safety_relevant"}
        and all(g < 0.04 for g in four_gates)
        and not precheck.catalogue_matches                    # deterministic, model-independent
        and (channel != "social_post" or post_nature == "PROMOTIONAL_OR_SPAM")):
    band = "GREEN_CLOSE"
else:
    band = "YELLOW_REVIEW"
```

- **A complaint with an adverse event is dual-processed** — both
  `product_complaint` and `safety_case`. A complaint must never swallow a case.
- **A model's `NOT_SAFETY_RELEVANT` can close nothing on its own.** It closes
  only through the `GREEN_CLOSE` gate, which also requires all four gates under
  0.04 *and* no product named by the deterministic pre-check.
- **QA sampling of closures:** a deterministic fraction of `GREEN_CLOSE`
  records (select by `int(state_sha256[:8], 16) % 100 < rate * 100`) gets a QA
  review job. The band stays `GREEN_CLOSE`; the sample is recorded. Demo rate
  is a policy value.
- **The numbers 0.04, 0.10 and 0.50 are demo policy values.** Put them in one
  versioned policy object with a comment saying they must be calibrated against
  a frozen gold set before any production use.

### 7.4 Failure is a decision too

If a provider times out or errors, retry with backoff; after the last attempt,
append a `sys1_decisions` row with `model_id = 'system/fail-closed'`,
`answers = {"failure": {…}}`, `confidence_band = 'YELLOW_REVIEW'`, null
probabilities. The record reaches a human and the ledger says why. When the
provider recovers, re-evaluation appends a new row under the real `model_id` —
the unique index allows it.

### 7.5 Providers

- **`DemoSystemOneProvider`** (default for `make demo`) implements
  `SystemOneClient` with deterministic keyword rules and fixed probabilities
  (strong evidence ≈ 0.92, weak ≈ 0.60, none ≈ 0.02). It must import nothing
  from `typesafe_sdk`. Every row it writes says `model_id = 'demo/keyword-stub'`
  and `sampler_version = 'demo-keyword-1'`. Lexicons should cover the fixtures,
  including Hinglish (`chakkar` = dizziness, `ulti` = vomiting) and negation
  ("No adverse event reported", "haven't taken any").
- **`DemoSystemTwoProvider`** fills templates: a short narrative citing exact
  offsets, and follow-up questions for missing criteria. `model_id =
  'demo/template'`.
- **Provider selection** by env `SYS1_PROVIDER=demo|typesafe|local` and
  `SYS2_PROVIDER=demo|anthropic|local`, defaulting to `demo` only when
  `VYOM_DEMO=1`. Outside demo mode, a missing provider config is a startup
  error, never a silent fallback to the stub.
- If `typesafe-sdk` cannot be installed from the configured index, move it to
  an optional extra `[typesafe]`. The demo must install and run without it.
- A Vertex AI provider is **out of scope**. If added later (ask first), it is a
  hosted provider and may serve `pv_literature` only.

### 7.6 If you touch the real Claude System Two client

The model ID stays pinned in `ANTHROPIC_SYSTEM2_MODEL`; do not hardcode or
change it. Current API constraints that will otherwise bite:

- Structured output goes in `output_config: {"format": {...}}`; the top-level
  `output_format` parameter is deprecated.
- Forced `tool_choice` (`{"type": "any"}` or `{"type": "tool", …}`) returns
  **400** on current Sonnet and Opus models. Use structured output, or
  `strict: true` on a tool with `tool_choice: {"type": "auto"}`.
- `thinking: {"type": "disabled"}` returns 400 on Claude Sonnet 5.5. Leave
  thinking at its default, and control cost with `output_config.effort`.
- Assistant-message prefill returns 400. Do not prefill.
- Check `stop_reason` before reading content. On `"refusal"` — possible with
  overdose or misuse text — append no draft, record why, and route the case to
  a human. Never crash, never auto-close.
- `pv_icsr` never calls the hosted Anthropic API; it uses the local System Two.

---

## 8. Dummy data — `vyom-os/fixtures/demo/`

Realistic in shape and messiness; fictional in every identity. Fifteen inputs.
**Process them in received/detected order, ties broken by fixture id**, so case
numbers are deterministic. Demo clock: `VYOM_DEMO_NOW=2026-10-31T12:00:00+05:30`,
reporting timezone `Asia/Kolkata`.

### 8.1 Five fixtures, verbatim

**`emails/e1_hcp_serious.eml`**
```
Message-ID: <e1.vy201.7c1f@clinic.example>
Date: Mon, 26 Oct 2026 09:14:00 +0530
From: "Dr. R. Example (FICTIONAL)" <r.example@clinic.example>
To: safety@demo-pharma.example
Subject: Suspected adverse reaction - VY-201
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Dear Safety Team,

I am reporting a suspected adverse reaction in a 62-year-old male patient
under my care. He started VY-201 40 mg once daily on 20 Oct 2026. On
23 Oct 2026 he developed a widespread itchy rash with blistering and was
admitted to hospital the same evening. VY-201 has been stopped.

I can be reached at this address or on +91 00000 00001 for follow-up.

Dr. R. Example (FICTIONAL)
Consultant Physician, Demo Clinic (FICTIONAL)
```

**`emails/e2_hcp_followup.eml`** — same thread; quoted text must not drive a duplicate match
```
Message-ID: <e2.vy201.91ad@clinic.example>
In-Reply-To: <e1.vy201.7c1f@clinic.example>
References: <e1.vy201.7c1f@clinic.example>
Date: Wed, 28 Oct 2026 16:40:00 +0530
From: "Dr. R. Example (FICTIONAL)" <r.example@clinic.example>
To: safety@demo-pharma.example
Subject: Re: Suspected adverse reaction - VY-201
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Follow-up on my earlier report. The rash resolved within 5 days of
stopping VY-201 and the patient was discharged on 27 Oct 2026. Liver
enzymes were normal throughout. He has also taken VY-412 for two years
with no change in dose.

> I am reporting a suspected adverse reaction in a 62-year-old male patient
> under my care.
```

**`forms/f1_hcp_webform.json`** — repeats E1 via a different channel and a spelling variant
```json
{
  "form_id": "WF-2026-000318",
  "submitted_at": "2026-10-27T11:05:00+05:30",
  "reporter": {
    "type": "healthcare_professional",
    "name": "Dr. R. Example (FICTIONAL)",
    "email": "r.example@clinic.example",
    "country": "IN"
  },
  "patient": { "age": 62, "sex": "male" },
  "product": "vy 201",
  "dose": "40 mg daily",
  "reaction": "Blistering skin rash, admitted to hospital",
  "onset_date": "2026-10-23",
  "consent_to_contact": true
}
```

**`social/s1_first_person_er.json`** — posted 28 Oct, detected by us 30 Oct; day zero is 30 Oct
```json
{
  "data": {
    "id": "1983000000000000101",
    "text": "3 days on VY-305 and I can't stop throwing up. ended up in the ER last night 🤢",
    "author_id": "900000000000000014",
    "created_at": "2026-10-28T18:20:00.000Z",
    "lang": "en",
    "conversation_id": "1983000000000000101"
  },
  "includes": {
    "users": [
      { "id": "900000000000000014", "username": "demo_user_014", "name": "Demo User 014 (FICTIONAL)" }
    ]
  },
  "_vyom": {
    "detected_at": "2026-10-30T07:12:00+05:30",
    "listener": "demo-social-poll",
    "query": "VY-305 OR vy305"
  }
}
```

**`social/s6_hinglish.json`** — Hinglish; the verbatim is stored as written, untranslated
```json
{
  "data": {
    "id": "1983000000000000106",
    "text": "vy305 lene ke baad kal se bahut chakkar aa rahe hain, normal hai kya?",
    "author_id": "900000000000000021",
    "created_at": "2026-10-30T22:15:00.000Z",
    "lang": "hi",
    "conversation_id": "1983000000000000106"
  },
  "includes": {
    "users": [
      { "id": "900000000000000021", "username": "demo_user_021", "name": "Demo User 021 (FICTIONAL)" }
    ]
  },
  "_vyom": { "detected_at": "2026-10-31T07:12:00+05:30", "listener": "demo-social-poll", "query": "VY-305 OR vy305" }
}
```

### 8.2 The other ten — write them to match these specifications

| Id | File | Channel | Time (IST) | Content |
| --- | --- | --- | --- | --- |
| E3 | `emails/e3_consumer_nonserious.eml` | email, from `a.demo@mail.example` "A. Demo (FICTIONAL)" | 27 Oct 10:02 | Mother, 70, mild headache most afternoons since starting VY-305 last week; goes away with rest; "Should we be worried?" |
| E4 | `emails/e4_product_complaint.eml` | email, `b.demo@mail.example` | 28 Oct 18:30 | VY-412 tablets in new strip, batch VYB-0042, discoloured and crumble; "I haven't taken any from this strip." |
| E5 | `emails/e5_complaint_with_ae.eml` | email, `c.demo@mail.example` | 29 Oct 09:50 | VY-412 from batch VYB-0042 crumbly; son (14) took one yesterday and vomited twice in the evening; fine today |
| S2 | `social/s2_sarcasm.json` | social | detected 30 Oct 07:12 | "this VY-201 schedule is literally killing me lol 4 pills a day 😩" |
| S3 | `social/s3_news_share.json` | social | detected 30 Oct 07:12 | "New study links VY-412 to liver problems 👀 https://news.example/vy412-study" |
| S4 | `social/s4_spam.json` | social | detected 30 Oct 07:12 | "Cheap meds online, no prescription needed!!! Fast delivery 👉 https://shop.example" |
| S5 | `social/s5_pregnancy.json` | social | posted 30 Oct 12:30Z, detected 30 Oct 19:12 | "Just found out I'm 8 weeks pregnant and I've been taking VY-201 the whole time. is that bad??" |
| C1 | `calls/c1_medical_inquiry.txt` | call transcript, header `CALL ID: CC-2026-10-30-0042`, `RECEIVED: 2026-10-30T15:20:00+05:30`, `AGENT: Agent 07 (FICTIONAL)`, `CALLER: consumer` | 30 Oct 15:20 | Asks whether VY-305 can be taken with alcohol at a family function. Asked about side effects: says no, feels fine. "No adverse event reported." Referred to Medical Information. |
| L1 | `literature/l1_case_report.json` | literature (`LiteratureRecord`) | ingested 29 Oct 06:00 | "Severe hepatotoxicity after VY-412: a case report (FICTIONAL)". 55-year-old woman, jaundice and markedly elevated liver enzymes eight weeks after starting VY-412, required hospitalisation; normalised after withdrawal. DOI `10.5555/demo.0001` (a test prefix). **No real-looking PMID.** |
| L2 | `literature/l2_animal_study.json` | literature | ingested 29 Oct 06:00 | "Effects of VY-201 on hepatic enzymes in rats (FICTIONAL)". Male rats, 28 days, no human subjects. DOI `10.5555/demo.0002`. |

All social fixtures carry the `_vyom` envelope and fictional `demo_user_0NN`
handles. Every email uses `To: safety@demo-pharma.example`.

### 8.3 Expected outcomes — encode as `fixtures/demo/expected.json`

Per input, in processing order:

| # | Id | Domain | Workflows | Band | Case | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | E1 | pv_icsr | safety_case | RED_ESCALATE | **VY-CASE-0001** | Phone and email redacted |
| 2 | E3 | pv_icsr | safety_case | YELLOW_REVIEW | **VY-CASE-0002** | Non-serious |
| 3 | F1 | pv_icsr | safety_case | RED_ESCALATE | → 0001 | `duplicate_of` via fuzzy fingerprint; same reporter key; `vy 201` matched |
| 4 | E2 | pv_icsr | safety_case | RED_ESCALATE | → 0001 | `follow_up_of` E1 via `deterministic_thread`; VY-412 is **concomitant**, not suspect |
| 5 | E4 | pv_icsr | product_complaint | YELLOW_REVIEW | — | No exposure, so no case |
| 6 | L1 | pv_literature | safety_case | RED_ESCALATE | **VY-CASE-0003** | Literature routing unchanged (policy v4) |
| 7 | L2 | pv_literature | not_safety_relevant | GREEN_CLOSE | — | Animal-only, all gates low |
| 8 | E5 | pv_icsr | product_complaint, safety_case | YELLOW_REVIEW | **VY-CASE-0004** | **Dual-processed.** Shares batch VYB-0042 with E4 |
| 9 | S1 | pv_icsr | safety_case | RED_ESCALATE | **VY-CASE-0005** | Provisionally serious: an ER visit alone is not hospitalisation; a physician decides |
| 10 | S2 | pv_icsr | not_safety_relevant | YELLOW_REVIEW | — | **Not auto-closed** — names VY-201, so the deterministic guard blocks closure |
| 11 | S3 | pv_icsr | literature_referral | YELLOW_REVIEW | — | News share; no identifiable patient |
| 12 | S4 | pv_icsr | not_safety_relevant | GREEN_CLOSE | — | No product, all gates low, spam |
| 13 | C1 | pv_icsr | medical_information | YELLOW_REVIEW | — | Negated AE must not create a case |
| 14 | S5 | pv_icsr | safety_case | YELLOW_REVIEW | **VY-CASE-0006** | Special situation: pregnancy exposure, no AE |
| 15 | S6 | pv_icsr | safety_case | YELLOW_REVIEW | **VY-CASE-0007** | Hinglish; non-serious |

Per case, with the demo clock policy (`demo-policy-1`: serious → 15 calendar
days, non-serious → 90, from provisional day zero = earliest receipt or
detection in the case; a follow-up carries its own due date from its own
receipt; special situation without an adverse reaction → no submission clock,
follow-up for outcome):

| Case | Day zero | Clock | Due | At demo-now | `event_verbatim` | Suspect / concomitant |
| --- | --- | --- | --- | --- | --- | --- |
| 0001 | 26 Oct 2026 | 15-day | 10 Nov 2026; follow-up due 12 Nov | DAY 5 OF 15 | widespread itchy rash with blistering | VY-201 / VY-412 |
| 0002 | 27 Oct 2026 | 90-day | 25 Jan 2027 | DAY 4 OF 90 | mild headache | VY-305 / — |
| 0003 | 29 Oct 2026 | 15-day | 13 Nov 2026 | DAY 2 OF 15 | jaundice and markedly elevated liver enzymes | VY-412 / — |
| 0004 | 29 Oct 2026 | 90-day | 27 Jan 2027 | DAY 2 OF 90 | vomited twice | VY-412 / — |
| 0005 | 30 Oct 2026 | 15-day (provisional serious) | 14 Nov 2026 | DAY 1 OF 15 | can't stop throwing up | VY-305 / — |
| 0006 | 30 Oct 2026 | none — follow-up for pregnancy outcome | — | — | — (special situation) | VY-201 / — |
| 0007 | 31 Oct 2026 | 90-day | 29 Jan 2027 | DAY 0 OF 90 | bahut chakkar aa rahe hain | VY-305 / — |

Day zero is **provisional** from receipt for any record not closed, so the
system never under-counts days; it is **confirmed** when a reviewer accepts
validity; it may move **earlier** if an earlier linked source appears, never
later. These are demo policy values — real profiles differ by region and are
Phase 4–5 work.

Graph checks: one `batch` node `VYB-0042` with two `mentions_batch` edges (E4,
E5). Case 0001 is one connected component: E1 ← `follow_up_of` E2, case ←
`duplicate_of` F1.

Follow-up drafts (never sent): for 0005, 0006 and 0007, missing patient and
contact details; for 0002, onset date and dose.

---

## 9. Milestones — stop and report after each

### M0 — Hygiene and baseline
1. Replace the root `.gitignore` (it currently holds only `*.tsbuildinfo`)
   with entries for `node_modules/`, `.next/`, `out/`, `.vercel/`,
   `__pycache__/`, `*.py[cod]`, `.venv/`, `*.egg-info/`, `.pytest_cache/`,
   `.DS_Store`, `.env`, `.env.*`, `!.env.example`, `demo-output/`.
2. `vyom-os/.env` is committed. Run `git rm --cached vyom-os/.env` (keeps the
   local file). **Tell the human in your report that the Postgres password in
   it must be rotated** — removing it from tracking does not remove it from
   history. Do not print its values. Do not rewrite history.
3. In a clean venv, `python -m pip install -e '.[test]'` and run the existing
   suite. Record the result as the baseline.

**Accept when:** `git status` shows no `.env`, `.next/` or `node_modules/`
noise; existing tests green; baseline recorded.

### M1 — Data model
Migration `004` per §5. Add an integration test that **tries an UPDATE and a
DELETE on every append-only table and asserts each raises** — these triggers
are the load-bearing compliance control and are currently untested.
Integration tests use `@pytest.mark.integration` and run when
`VYOM_TEST_DATABASE_URL` is set; otherwise they skip with that reason in the
message.

**Accept when:** 002 → 003 → 004 apply cleanly to an empty database twice in a
row (idempotent `if not exists`); trigger tests pass against the demo
database.

### M2 — Channels, normalisation, redaction
Adapters, `ChannelMessage`, normalised state, redaction, pseudonymisation and
pre-checks per §6. All 15 fixtures. Unit tests, no database.

**Accept when:** every fixture parses; no email address, phone number or handle
from any fixture appears anywhere in any normalised state; every catalogue match
and date has offsets that slice the redacted text back to its surface form;
emoji and romanised Hinglish survive intact; the same input always
produces the same `state_sha256`.

### M3 — Providers and routing
Per-domain versions, schema v3 questions, policy v5, fail-closed decision, demo
providers, provider selection — §7.

**Accept when:** literature and RCM routing tests are unchanged and green; a
parametrised test asserts `safety_email`, `web_form`, `social_post` and
`call_transcript` all use the **local** client; the stub is deterministic;
`GREEN_CLOSE` is impossible when `catalogue_matches` is non-empty (test it
with every other condition satisfied); a provider exception produces a
`system/fail-closed` row in `YELLOW_REVIEW` and never a closure.

### M4 — Pipeline orchestration
`pipeline_jobs`, stages, `vyom-worker --drain [--domains …]`, retries with
backoff, leases, injected clock.

**Accept when:** running the whole demo twice creates **zero** new states,
decisions, edges or clock events the second time; two concurrent workers never
process the same job; a worker started with `--domains pv_icsr` never claims a
literature job.

### M5 — Nucleus: graph and case assembly
Deterministic links first (email thread, exact content hash), then fuzzy
duplicate detection on the extracted fields: same suspect product, and either
the same reporter key or (age ±1, same sex, event-verbatim token overlap,
onset within ±3 days). Score ≥ 0.85 links `duplicate_of`; 0.60–0.85 links
`possible_duplicate_of` for a reviewer to decide and **merges nothing**. Never
auto-merge across different reporters without that evidence. Threshold values
are demo policy. Case = connected component over `derived_from`,
`follow_up_of`, `duplicate_of`.

**Accept when:** the case table in §8.3 is reproduced exactly; E2's quoted
reply text does not produce a fuzzy duplicate edge (the thread edge wins); every
edge carries method, score and rule version.

### M6 — Assure and comply
Checks: missing minimum criteria (which of the four), unknown product, date
logic (onset before exposure, onset after receipt, future dates), seriousness
language inconsistent with the seriousness probability, more than one
catalogue product (reviewer confirms the suspect), follow-up contradicting the
initial report, attachment not processed. Clock events per §8.3.
`vyom-demo audit-pack VY-CASE-0001` writes every source, normalised state with
its hash, decision with its versions, edge with its evidence, finding, clock
event and human label for the case — and recomputes every `state_sha256` to
prove nothing drifted.

**Accept when:** every due date and DAY X OF Y in §8.3 matches; the audit pack
for 0001 contains E1, E2 and F1 and its hash check passes.

### M7 — Report, simulated review and `make demo`
- `vyom-demo review --simulate` appends `human_labels` for every safety case
  as reviewer `demo-reviewer (FICTIONAL)`, role `safety_physician`, rationale
  `"SIMULATED REVIEW — DEMO"`. It is visibly a simulation in the ledger.
- `report/e2b_draft.py` turns each accepted case into **E2B(R3)-shaped DRAFT**
  XML using the Appendix B mapping, with a header comment
  `DRAFT — not validated against the ICH schema — not for submission`.
- `vyom-demo report` writes `demo-output/`: `summary.json`, `cases.md` (per
  case: sources, graph links with evidence, workflows, band, clock, findings,
  follow-up questions), `screening-log.csv`, `e2b/VY-CASE-000N.xml`.
- `docker-compose.demo.yml` — **standalone**, not an override: its own
  `postgres` on `127.0.0.1:55432`, database `vyom_demo`, fixed demo-only
  credentials that are never reused anywhere.
- `make demo`: start demo Postgres → wait healthy → apply 002, 003, 004 →
  `vyom-demo reset --yes` → `run` → `review --simulate` → `export` → `report`
  → print the §0 summary table.
- `vyom-demo reset` **refuses** unless the database name is exactly
  `vyom_demo` and the host is local. It drops and recreates the schema, because
  the triggers rightly forbid deleting rows.

**Accept when:** `make demo` from a clean checkout ends with the §0 table and
the §8.3 tables reproduced; a golden test compares the run to
`expected.json`; nothing leaves the machine.

### M8 — Infrastructure
1. `docker-compose.yml` gains a `worker` service; the existing services keep
   working.
2. `deploy/k8s/base` + `overlays/dev` + `overlays/prod` (kustomize, plain
   manifests — no Helm):
   - Deployment `vyom-api` (+ Service), liveness/readiness on `/healthz`.
   - **Two worker Deployments** from the same image:
     `vyom-worker-public` (`--domains pv_literature`) and
     `vyom-worker-phi` (`--domains pv_icsr`).
   - **NetworkPolicy:** `vyom-worker-phi` may reach only Postgres and the
     in-cluster local model Service — all other egress denied. This enforces
     the PHI boundary a second time, at the network layer, so a routing bug
     cannot leak `pv_icsr` to a hosted endpoint. Note in a comment that this
     needs a CNI that enforces NetworkPolicy.
   - CronJobs: literature sweep, mailbox poll, social poll, weekly report.
     **Mailbox and social pollers ship `suspend: true`** — live connectors stay
     off until a human enables them.
   - Job: migrations. ConfigMap for non-secret config. `secret.example.yaml`
     with **key names and empty values only**.
   - Non-root containers, resource requests and limits.
   - `overlays/dev` may run in-cluster Postgres; `overlays/prod` expects managed
     Postgres via a Secret, with a comment that the region must satisfy the
     tenant's residency commitment.
3. If `.github/workflows/` has no Python CI, add one that runs the unit suite
   and the integration suite against a Postgres service container.

**Accept when:** `kubectl kustomize deploy/k8s/overlays/dev` and `…/prod`
render without error (if `kubectl` is not installed, say so and skip — do not
add a Python YAML dependency to test it); no manifest contains a secret value.

### M9 — Optional: show it in the console (**ask before starting**)
Only if the human approves: a read-only queue view in the existing
`vyom-web/src/app/(platform)/[tenant_slug]/console`, reading
`GET /v1/review/queue` through `vyom-web/src/lib/gateway/api-client.ts`.
Follow `DESIGN.md`, all `CLAUDE.md` content rules, `npm run check`, and
Playwright screenshots at 375, 768 and 1440 px. Do not introduce a new sample
tenant or identifier format in the UI — that needs the owner to amend
`CLAUDE.md` first.

---

## 10. Tests that must exist when you are done

| Invariant | Test |
| --- | --- |
| PHI boundary | Every non-literature channel resolves to `pv_icsr` and the local client |
| Append-only | UPDATE and DELETE raise on every evidence table |
| One autonomous path | No `GREEN_CLOSE` with a catalogue match; no closure from a failure |
| Dual processing | Complaint plus AE produces both workflows (E5) |
| Idempotency | Second full run adds nothing |
| Determinism | Same inputs → same hashes, case numbers, edges, dates |
| Redaction | No raw email, phone or handle in any normalised state or model input |
| Evidence | Every `event_verbatim` slices from the stored text at its offsets |
| Clock | Day zero never moves later; due dates match §8.3 |
| Golden run | Full demo matches `expected.json` |
| Literature unchanged | Existing literature and RCM routing tests pass unmodified |

---

## 11. Report back after every milestone

```
## Mx report
Done:          what changed, by file
Acceptance:    each criterion -> pass/fail, with the command and an output excerpt
Tests:         N passed, M skipped (reason for each skip)
Deviations:    anything you did differently from this spec, and why
Needs a human: decisions only the owner can make
```

Things that will need a human, so raise them rather than decide them:
rotating the committed Postgres password; legal review before any live social
connector (Appendix A); approving M9; adding any dependency; whether demo
policy thresholds become a starting point for real calibration.

---

## Appendix A — real-world connectors: what must be true before building them

- **Social platforms.** Platform developer terms commonly restrict deriving
  health information about individual users. Have counsel review the current
  terms of each platform before any live connector exists, and decide whether
  you listen only to accounts and pages you own. Expect API access to be paid.
- **Regulation.** EU GVP Module VI addresses suspected reactions found on the
  internet and in digital media. Confirm with your QPPV which sources you are
  obliged to screen and how day zero applies to each, then scope the connector
  to that — not to everything the API allows.
- **Personal data.** Handles and posts are personal data under India's DPDP Act
  and the GDPR. Pseudonymise on ingest, minimise what you keep, set retention.
- **Email.** Poll a dedicated safety mailbox with least-privilege credentials
  held in a secret store. Record received time from the mail server, not the
  sender's `Date` header, once you have a real server — the demo uses `Date`.
- **No automated replies, on any channel.** Ever.

## Appendix B — E2B(R3)-shaped draft mapping

Section letters follow ICH E2B(R3). **Verify every element ID against the ICH
E2B(R3) Implementation Guide before Phase 4** — this draft is a shape, not a
submission.

| E2B(R3) section | Draft field | Source |
| --- | --- | --- |
| C.1 Identification of the case safety report | Report id `IN-DEMOPHARMA-VY-CASE-000N`, creation date, report type (spontaneous / literature), date first received (day zero), date of most recent information | Case, clock |
| C.2.r Primary source | Qualification (HCP / consumer), country | Reporter node, form |
| C.4.r Literature reference | Citation, DOI | Literature cases only |
| D Patient | Age at onset, sex — never a name | Extracted fields |
| E.i Reaction / event | Verbatim as reported; MedDRA term **left empty — "NOT CODED — licence required"**; seriousness criteria; outcome | Ledger, follow-ups |
| G.k Drug information | Product as reported, characterisation (suspect / concomitant), dose | `mentions_product` edges with `role` |
| H Narrative | The reviewer-accepted narrative | `sys2_syntheses` + `human_labels` |
