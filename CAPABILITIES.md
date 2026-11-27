# What Vyom does today

The state of the pharmacovigilance MVP on branch `mvp/pv-suite`, as of
2026-11-27. Use this list before promising anything to a client. If a
capability is not under **Shipped**, describe it as planned.

- **Shipped:** built, covered by tests, and checked in the console against a
  running Vyom OS.
- **Demo only:** works end to end with the rule-based demo engine
  (`VYOM_AI_MODE=demo`) or with fixtures. The live path exists in code but has
  not run against the real service.
- **Planned:** not built.

## How it was checked

- **124 backend tests pass**, including PostgreSQL integration tests. These
  cover row-level security between tenants, the migration runner and the
  operator commands.
- **Console, live mode:** walked through for each role (reviewer, safety
  physician, QPPV, tenant admin, ops) against a local Vyom OS. This covered
  sign-in, screening decisions, case intake to approval, E2B export, and
  report authoring to sign-off.
- **Console, sample workspace:** every page at 375, 768 and 1440 px, with no
  horizontal scroll.
- **Production build:** the console's standalone server build. This covered
  the health check, live sign-in, `Secure` and `HttpOnly` session cookies,
  and turning the sample workspace off.
- **Not yet run:**
  - building the Docker images and running the Compose stack, because Docker
    was unavailable on the build machine;
  - anything on GCP;
  - Vertex AI;
  - PubMed from a deployment. The PubMed client is tested with mocked
    responses.

## Radar — literature screening

| Capability | State |
| --- | --- |
| Weekly sweep per product (PubMed; Europe PMC optional), as a Monday CronJob | Shipped (fixtures); live PubMed is Demo only |
| Append-only ledger of every article and decision, with model, sampler, schema and threshold versions | Shipped |
| Screening questions with answer probabilities, routed to red / yellow / green bands by a deterministic router | Shipped; the answers come from the demo engine until Vertex is live |
| Reviewer decision: valid ICSR, safety information, not relevant, or escalate | Shipped |
| Escalation to the safety physician, who alone decides escalated articles | Shipped |
| A valid-ICSR decision opens a case, with day zero set to the decision date | Shipped |
| Duplicate articles across sources folded into one record | Shipped |
| Auto-close of green-band articles | Off by default; every article gets a human decision |
| Sweep failure raised as an ops alert while other tenants continue | Shipped |
| Full-text retrieval, local-literature sources, client search strategies beyond product terms | Planned |

## Verify — case processing

| Capability | State |
| --- | --- |
| Intake by pasting a safety email, call transcript or manual entry | Shipped |
| Intake from PDF or scanned forms (OCR) | Planned; needs a new dependency |
| Structured-field extraction, with evidence pointers into the source text | Demo only (rule-based stand-in); Vertex path written, not run |
| Validity (four minimum criteria), seriousness, expectedness against the product's reference safety information, and the 15- or 90-day clock, all by deterministic, versioned rules | Shipped |
| Possible duplicates and similar reports | Shipped |
| Event coding: the 27 MedDRA system organ classes without a licence; lowest-level and preferred-term suggestions once the client loads its own MedDRA release | Shipped (licence boundary); never ships dictionary content |
| Narrative draft for the reviewer to edit | Demo only |
| Causality by the safety physician; approval; every change versioned with who, why and lineage | Shipped |
| E2B(R3) export: a reviewable data-element document with a SHA-256 hash | Shipped as a **draft**. It is not a validated HL7 ICSR message, and there is no gateway submission |
| Follow-up requests, gateway acknowledgements (ACKs), submissions to authorities | Planned |

## Dossier — periodic reports

| Capability | State |
| --- | --- |
| PBRER (ICH E2C(R2) section layout) and PADER for a product, interval and data lock point | Shipped |
| Aggregates and tabulations computed from approved cases and screened literature | Shipped |
| Narrative sections drafted from aggregates only; citations and numbers checked against the data | Demo only |
| Sections that need company input stay flagged until a person writes them; accept or edit, with a reason | Shipped |
| QPPV sign-off: password re-entry, a stated meaning, the signed version, blocked while any draft or input is outstanding | Shipped |
| Markdown export | Shipped |
| Comments on sections | Planned (not stored today) |
| DOCX or PDF output, DSUR, RMP, signal assessment reports | Planned |

## Signal management

| Capability | State |
| --- | --- |
| Provenance-first evidence graph linking articles, cases, products and events (it never asserts causality) | Shipped as a data layer; no signal screen yet |
| Signal detection, validation and tracking | Planned (roadmap) |

## Console and platform

| Capability | State |
| --- | --- |
| Dashboard: literature by band, cases by status and clock, reports, model-call usage | Shipped |
| Audit trail: every change, decision and sign-off; cannot be edited or deleted from the application | Shipped |
| Settings: tenant, members, which model handles which data | Shipped |
| `/ops`: cross-tenant health and alerts (Vyom operations role only) | Shipped |
| Multi-tenant isolation by PostgreSQL row-level security; every request is scoped to one tenant | Shipped |
| Roles and permissions from a policy table (reviewer, safety physician, QPPV, admin, ops) | Shipped |
| Password sign-in (scrypt), 8-hour signed session, sign-in throttle | Shipped; the throttle is per API replica |
| MFA, SSO (SAML / OIDC), self-service password reset | Planned |
| AI gateway: public literature to the hosted model; identifiable case data to it only with the client's approval and in the client's region; otherwise an in-network model or manual entry | Shipped (policy and tests); Vertex not run |
| Fictional sample workspace (Demo Pharma) that needs no backend | Shipped |
| Onboarding through `vyom-admin`: tenants, users, products, disabling accounts | Shipped |
| Tenant data export and deletion at the end of a contract | Planned |
| Admin screens for users and products (today they are command-line only) | Planned |

## Deployment

| Capability | State |
| --- | --- |
| Dockerfiles for both apps (non-root, read-only root filesystem in the cluster) | Written; **images not yet built** |
| Docker Compose stack for a laptop or a demo machine | Written and validated with `docker compose config`; **not yet run** |
| GKE Autopilot manifests: Cloud SQL Auth Proxy sidecar, Workload Identity, managed TLS, NetworkPolicies, the restricted Pod Security level, the migration Job and the weekly CronJob | Written; render with `kubectl kustomize`; **not yet applied** |
| Migration runner with a checksum ledger, and refusal of edited history | Shipped |
| Runbook: setup, release, rollback, onboarding, backups, rotation | `deploy/RUNBOOK.md` |

## Open risks before a client pilot

See the checklist in `deploy/RUNBOOK.md` §9. In short:

- Cloud SQL must accept the `bypassrls` role.
- TLS may terminate outside the region on the global load balancer.
- In-cluster traffic is plain HTTP.
- No MFA.
- The sign-in throttle is per replica.
- Vertex models must be chosen and evaluated.
- Images must be pinned by digest.
- A restore must be rehearsed.
- The client's validation approach must be agreed.
- Credentials exposed during development must be rotated.
- The console host also serves the public pages. Point `NEXT_PUBLIC_SITE_URL`
  at the public site, and add a redirect for marketing paths on the console
  host before launch.
