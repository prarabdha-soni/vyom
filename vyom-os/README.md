# Vyom OS

The FastAPI backend for Vyom's pharmacovigilance suite: literature screening
(Radar), case processing (Verify) and periodic reports (Dossier). The package
is `vyom_os`. `vyom_literature` is the earlier prototype; Vyom OS reuses its
literature sources and Vertex AI client.

- How to deploy it: `../deploy/RUNBOOK.md`.
- What is shipped and what is planned: `../CAPABILITIES.md`.

## Run it locally

Python 3.11 or newer, and PostgreSQL 16:

```sh
python -m pip install -e '.[test]'
```

Apply the migrations with an owner connection, then start the API with the
two application roles:

```sh
MIGRATION_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/vyom vyom-migrate
```

```sh
DATABASE_URL=postgresql://vyom_service:…@127.0.0.1:5432/vyom \
APP_DATABASE_URL=postgresql://vyom_app:…@127.0.0.1:5432/vyom \
VYOM_SESSION_SECRET=… vyom-os-api
```

Set both URLs explicitly; a `.env.local` in this directory is also read, but
never commit it. The API binds to `127.0.0.1:8000`. To run the whole stack in
containers instead, use `docker compose -f ../deploy/compose.yaml` (see the
runbook, §1).

| Command | What it does |
| --- | --- |
| `vyom-os-api` | The API (`API_HOST`, `API_PORT`) |
| `vyom-migrate` | Applies `migrations/002…` in order, each exactly once, and records each file's checksum in `schema_migrations`. It refuses edited history. `--status` reports only; `--baseline` adopts a database migrated by hand. It also sets the `vyom_app` and `vyom_service` passwords from `VYOM_APP_DB_PASSWORD` and `VYOM_SERVICE_DB_PASSWORD` |
| `vyom-admin` | `create-ops-tenant`, `create-tenant`, `add-user`, `disable-user`, `add-product`, `list`; every change is audited |
| `vyom-seed-demo --confirm-fictional` | The fictional `demo-pharma` tenant and its sample work (`VYOM_DEMO_PASSWORD`). Never on a client database |
| `vyom-weekly-sweep` | The literature sweep for every client tenant (`--include-fictional` for the demo) |
| `vyom-terminology-load` | Loads a tenant's own licensed MedDRA release |

## Configuration

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | `vyom_service`, which bypasses row-level security: sign-in, jobs, `vyom-admin` |
| `APP_DATABASE_URL` | `vyom_app`, which is subject to row-level security: every request |
| `VYOM_SESSION_SECRET` | At least 32 characters, shared with the console |
| `VYOM_AI_MODE` | `demo` (the rule-based engine, with no network calls) or `live` |
| `VERTEX_PROJECT_ID`, `VERTEX_REGION`, `VERTEX_MODEL_ID`, `VERTEX_DRAFTING_MODEL_ID`, `VERTEX_SAMPLER_VERSION` | Live mode. Credentials come from Workload Identity, never from a key file |
| `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_API_KEY` | Optional. An in-network, OpenAI-compatible model for case data that may not leave the client's network |
| `NCBI_TOOL`, `NCBI_EMAIL`, `NCBI_API_KEY`, `VYOM_EUROPEPMC` | Live literature sources |
| `VYOM_TIMEZONE` | Default `Asia/Kolkata` |
| `VYOM_SESSION_TTL_SECONDS` | Default 8 hours |
| `VYOM_API_DOCS` | Serves the OpenAPI docs when set to `true` |

## Legacy prototype (`vyom_literature`)

The commands `vyom-fetch`, `vyom-sweep`, `vyom-api`, `vyom-gold-import`,
`vyom-report` and `vyom-export-training` belong to the earlier prototype. The
docs below describe it and are kept for reference.

Required for v2:

- `DATABASE_URL` pointing at the v2 PostgreSQL database.
- `TYPESAFE_API_KEY` and a pinned `CLOUD_SYS1_MODEL` for public literature.
- `LOCAL_SYS1_API_KEY`, `LOCAL_SYS1_BASE_URL`, and a pinned `LOCAL_SYS1_MODEL` for identifiable ICSRs.
- `ANTHROPIC_API_KEY` and a pinned `ANTHROPIC_SYSTEM2_MODEL` for public-literature synthesis; a local `LOCAL_SYS2_BASE_URL` and `LOCAL_SYS2_MODEL` handle ICSR synthesis.
- `SYS1_SAMPLER_VERSION` to record the exact sampler/runtime version.
- `API_BEARER_TOKEN` for service-to-service endpoints and `REVIEWER_TOKENS_JSON` mapping reviewer tokens to `{ "id": "UUID", "role": "safety_physician" }` identities.
- `NCBI_TOOL` and `NCBI_EMAIL` for PubMed; `NCBI_API_KEY` is optional.

The local endpoint must implement the TypeSafe `system_one` request/response contract. A plain Ollama-compatible `/v1` endpoint is not sufficient evidence of compatibility. Contract-test it with synthetic data before sending PHI. `pv_literature` is the only domain routed to the hosted client; `pv_icsr` routes locally.

Migrations are applied with `vyom-migrate` (above), never with `psql -f`.

Add versioned public-literature strategies to `strategies`, for example:

```sql
insert into strategies (domain, target_key, source, query_or_rules, version)
values ('pv_literature', 'atorvastatin', 'pubmed', '{"query":"atorvastatin"}', 1);
```

Run a dated sweep:

```sh
vyom-sweep --from-date 2026-10-13 --to-date 2026-10-14
```

Run the local API:

```sh
vyom-api
```

It binds to `127.0.0.1:8000` by default. Put it behind TLS and an approved network boundary before remote access. Service routes require `API_BEARER_TOKEN`; reviewer queue/action/report routes require a reviewer token from `REVIEWER_TOKENS_JSON`. This is a prototype token map, not enterprise SSO/RBAC.

Implemented API routes: `GET /healthz`, `POST /v1/icsr/intake`, `POST /v1/literature/sweep`, `GET /v1/review/queue`, `POST /v1/review/states/{state_id}/actions`, `GET /v1/reports/gold/{gold_set_version}`, and `GET /v1/reports/screening-log`.

Import an independently adjudicated, frozen public-PV gold CSV with columns `state_id,is_valid_case,rationale_note`:

```sh
vyom-gold-import gold-v1.csv --version gold-v1 --adjudicator-id 00000000-0000-4000-8000-000000000001
```

Generate the weekly screening log plus gold-set recall/precision report:

```sh
vyom-report --gold-set-version gold-v1 --model-id "$CLOUD_SYS1_MODEL" \
	--sampler-version "$SYS1_SAMPLER_VERSION" --question-schema-version 2 \
	--threshold-policy-version 4 --output weekly-report.json
```

Export correction examples for offline local work only (this does not train or upload a model):

```sh
ENABLE_TRAINING_EXPORT=true TRAINING_EXPORT_DIR=./local-training-exports \
	vyom-export-training --days 7
```

The exporter includes only public PV pool corrections, excludes frozen gold states, and creates owner-only JSONL files. It never exports identifiable ICSR states.

The sweep preserves raw source payloads, deduplicates canonical public states, records the state hash and model/schema/policy lineage, and skips decisions already recorded for the same pinned versions. It does not submit claims, generate regulatory outputs, or establish recall/calibration claims.

## Tests

Unit tests use mock records and fake providers. They call no external
service:

```sh
python -m pytest
```

The PostgreSQL integration tests also run when you point them at a server
where they may create and drop scratch databases and the two application
roles:

```sh
VYOM_TEST_PG_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres python -m pytest
```
