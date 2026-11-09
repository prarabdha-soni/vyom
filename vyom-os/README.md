# Vyom OS Engine

This directory is **vyom-os** (FastAPI). It contains two distinct paths:

- **v1 prototype:** the earlier PubMed/Europe PMC fetcher and Claude batch flow (`vyom-fetch`).
- **v2 foundation:** System One routing, an append-only decision ledger, and a public-literature sweep (`vyom-sweep`).

The v2 path includes structured hospital preflight and ICSR intake APIs, a public-literature sweep, selective System Two drafting, reviewer APIs, and gold-based evaluation. OCR/PDF extraction, a browser workbench, FHIR NHCX and E2B(R3) serializers, automated scheduling, enterprise identity, and production authorization remain deployment/product work.

## Setup

Use Python 3.11 or newer:

```sh
python -m pip install -e '.[test]'
cp .env.example .env.local
```

Fill `.env.local` locally. Never commit it or paste secrets into chat. Use a rotated Postgres credential and URL-encode reserved characters in `DATABASE_URL`.

Start the Docker Compose services with the same local environment file:

```sh
docker compose --env-file .env.local up --build
```

Required for v2:

- `DATABASE_URL` pointing at the v2 PostgreSQL database.
- `TYPESAFE_API_KEY` and a pinned `CLOUD_SYS1_MODEL` for public literature.
- `LOCAL_SYS1_API_KEY`, `LOCAL_SYS1_BASE_URL`, and a pinned `LOCAL_SYS1_MODEL` for identifiable ICSRs and hospital data.
- `ANTHROPIC_API_KEY` and a pinned `ANTHROPIC_SYSTEM2_MODEL` for public-literature synthesis; a local `LOCAL_SYS2_BASE_URL` and `LOCAL_SYS2_MODEL` handle PHI-domain synthesis.
- `SYS1_SAMPLER_VERSION` to record the exact sampler/runtime version.
- `API_BEARER_TOKEN` for service-to-service endpoints and `REVIEWER_TOKENS_JSON` mapping reviewer tokens to `{ "id": "UUID", "role": "safety_physician" }` identities.
- `NCBI_TOOL` and `NCBI_EMAIL` for PubMed; `NCBI_API_KEY` is optional.

The local endpoint must implement the TypeSafe `system_one` request/response contract. A plain Ollama-compatible `/v1` endpoint is not sufficient evidence of compatibility. Contract-test it with synthetic data before sending PHI. `pv_literature` is the only domain routed to the hosted client; `pv_icsr` and `hospital_rcm` route locally.

Apply the additive v2 schemas to a fresh or deliberately prepared database in order:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/002_system_one_decision_ledger.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/003_gold_set_labels.sql
```

The older `001_initial_schema.sql` belongs to the v1 prototype and is not required by v2. Review and back up any non-empty database before applying migrations.

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

Implemented API routes: `GET /healthz`, `POST /v1/rcm/preflight`, `POST /v1/icsr/intake`, `POST /v1/literature/sweep`, `GET /v1/review/queue`, `POST /v1/review/states/{state_id}/actions`, `GET /v1/reports/gold/{gold_set_version}`, and `GET /v1/reports/screening-log`.

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

The exporter includes only public PV pool corrections, excludes frozen gold states, and creates owner-only JSONL files. It never exports hospital RCM or identifiable ICSR states.

The sweep preserves raw source payloads, deduplicates canonical public states, records the state hash and model/schema/policy lineage, and skips decisions already recorded for the same pinned versions. It does not submit claims, generate regulatory outputs, or establish recall/calibration claims.

## Tests

Tests use mock records, fake providers, and an in-memory ledger double; they do not connect to Supabase or call TypeSafe:

```sh
python -m pytest
```