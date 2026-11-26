-- 009: Drug-safety MVP — products, case processing, periodic reports, audit trail.
--
-- Builds on 002–008 without rewriting them:
--   * ledger rows take their tenant from the transaction's app.tenant_id, so
--     existing ledger functions become tenant-aware without new parameters;
--   * source identifiers are unique per tenant (two clients may screen the
--     same PubMed record);
--   * new tables are tenant-scoped with forced row-level security;
--   * decision-like tables are append-only via reject_ledger_mutation().
-- Apply after 008 to a fresh or deliberately prepared database.

begin;

-- ---------------------------------------------------------------------------
-- Tenant scope helper. Empty or unset app.tenant_id yields NULL (fail closed).
-- ---------------------------------------------------------------------------
create or replace function app_tenant_id() returns uuid
language sql stable as $$
  select nullif(current_setting('app.tenant_id', true), '')::uuid
$$;

-- Ledger rows inherit the transaction tenant. The bootstrap fallback keeps
-- the legacy single-tenant CLI path working on service connections; on the
-- vyom_app role the RLS WITH CHECK still rejects a row without a tenant.
do $$
declare
  t text;
begin
  foreach t in array array[
    'clinical_states', 'source_records', 'sys1_decisions', 'sys2_syntheses',
    'human_labels', 'strategies', 'gold_set_labels'
  ] loop
    execute format(
      'alter table %I alter column tenant_id set default '
      'coalesce(app_tenant_id(), ''00000000-0000-0000-0000-000000000001''::uuid)', t
    );
  end loop;
  foreach t in array array[
    'evidence_spans', 'graph_edges', 'awareness_events', 'case_ready_drafts'
  ] loop
    execute format('alter table %I alter column tenant_id set default app_tenant_id()', t);
  end loop;
end $$;

-- Source identifiers are unique per tenant, not globally.
alter table source_records drop constraint if exists source_records_source_source_uid_key;
alter table source_records drop constraint if exists source_records_tenant_source_uid;
alter table source_records add constraint source_records_tenant_source_uid
  unique (tenant_id, source, source_uid);

-- New intake sources: synthetic demo literature and manual / web-form entry.
alter table strategies drop constraint if exists strategies_source_check;
alter table strategies add constraint strategies_source_check
  check (source in (
    'pubmed', 'europepmc', 'partner_e2b', 'safety_email', 'call_transcript',
    'hospital_adr_form', 'demo_fixture', 'manual_entry'
  )) not valid;

alter table source_records drop constraint if exists source_records_source_check;
alter table source_records add constraint source_records_source_check
  check (source in (
    'pubmed', 'europepmc', 'partner_e2b', 'safety_email', 'call_transcript',
    'hospital_adr_form', 'demo_fixture', 'manual_entry'
  )) not valid;

-- QPPV can record literature review labels.
alter table human_labels drop constraint if exists human_labels_reviewer_role_check;
alter table human_labels add constraint human_labels_reviewer_role_check
  check (reviewer_role in (
    'safety_physician', 'pv_associate', 'cpc_coder', 'tpa_auditor', 'qppv'
  )) not valid;

-- ---------------------------------------------------------------------------
-- Tenant settings used by the deterministic rules.
-- ---------------------------------------------------------------------------
alter table tenants add column if not exists kind text not null default 'mah'
  check (kind in ('mah', 'service_provider', 'internal'));
alter table tenants add column if not exists is_fictional boolean not null default false;
alter table tenants add column if not exists clock_policy jsonb not null default
  '{"version": "clock.v1", "serious_days": 15, "non_serious_days": 90}'::jsonb;

-- ---------------------------------------------------------------------------
-- Products and their reference safety information (expectedness source).
-- ---------------------------------------------------------------------------
create table if not exists products (
  id                        uuid primary key default gen_random_uuid(),
  tenant_id                 uuid not null default app_tenant_id() references tenants(id),
  code                      text not null check (length(code) between 1 and 64),
  name                      text not null,
  active_ingredient         text not null,
  dosage_form               text,
  strength                  text,
  international_birth_date  date,
  reference_safety_terms    jsonb not null default '[]'::jsonb,
  rsi_version               text not null default 'v1',
  active                    boolean not null default true,
  created_at                timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists tenant_counters (
  tenant_id  uuid not null default app_tenant_id() references tenants(id),
  name       text not null,
  value      bigint not null default 0 check (value >= 0),
  primary key (tenant_id, name)
);

-- ---------------------------------------------------------------------------
-- Case processing. `cases` is the mutable head; every change is an
-- append-only case_versions row plus an audit_events row.
-- ---------------------------------------------------------------------------
create table if not exists cases (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null default app_tenant_id() references tenants(id),
  case_number      text not null,
  product_id       uuid references products(id),
  source_channel   text not null check (source_channel in (
    'literature', 'safety_email', 'call_transcript', 'manual_entry', 'partner_e2b'
  )),
  source_state_id  bigint references clinical_states(id),
  status           text not null check (status in (
    'data_entry', 'medical_review', 'approved', 'closed_invalid', 'duplicate'
  )),
  current_version  int not null default 0 check (current_version >= 0),
  serious          boolean,
  day_zero         date not null,
  received_at      timestamptz not null default now(),
  created_by       uuid references user_accounts(id),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (tenant_id, case_number)
);
create index if not exists cases_tenant_status_idx on cases (tenant_id, status, day_zero);
create index if not exists cases_tenant_product_idx on cases (tenant_id, product_id, day_zero);

create table if not exists case_versions (
  id           bigserial primary key,
  tenant_id    uuid not null default app_tenant_id() references tenants(id),
  case_id      uuid not null references cases(id),
  version      int not null check (version > 0),
  payload      jsonb not null,
  assessments  jsonb not null,
  author_kind  text not null check (author_kind in ('ai', 'human', 'system')),
  author_id    uuid references user_accounts(id),
  reason       text not null check (length(reason) between 1 and 500),
  lineage      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  unique (case_id, version)
);

create table if not exists case_exports (
  id              bigserial primary key,
  tenant_id       uuid not null default app_tenant_id() references tenants(id),
  case_id         uuid not null references cases(id),
  case_version    int not null check (case_version > 0),
  format          text not null check (format in ('e2b_r3_data_elements_xml')),
  content         text not null,
  content_sha256  char(64) not null check (content_sha256 ~ '^[0-9a-f]{64}$'),
  created_by      uuid references user_accounts(id),
  created_at      timestamptz not null default now()
);

-- Reviewer outcome for a screened literature record.
create table if not exists literature_outcomes (
  id             bigserial primary key,
  tenant_id      uuid not null default app_tenant_id() references tenants(id),
  state_id       bigint not null references clinical_states(id),
  decision_id    bigint references sys1_decisions(id),
  outcome        text not null check (outcome in (
    'valid_icsr', 'safety_information', 'not_relevant', 'escalated'
  )),
  reason         text check (reason is null or length(reason) <= 2000),
  reviewer_id    uuid not null references user_accounts(id),
  reviewer_role  text not null,
  case_id        uuid references cases(id),
  created_at     timestamptz not null default now()
);
create index if not exists literature_outcomes_state_idx
  on literature_outcomes (state_id, created_at desc, id desc);

-- ---------------------------------------------------------------------------
-- Periodic safety reports (PBRER/PSUR and PADER drafting).
-- ---------------------------------------------------------------------------
create table if not exists periodic_reports (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null default app_tenant_id() references tenants(id),
  report_number    text not null,
  product_id       uuid not null references products(id),
  report_type      text not null check (report_type in ('pbrer', 'pader')),
  interval_start   date not null,
  data_lock_point  date not null,
  status           text not null check (status in ('draft', 'signed_off')),
  current_version  int not null default 0 check (current_version >= 0),
  created_by       uuid references user_accounts(id),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (tenant_id, report_number),
  check (data_lock_point >= interval_start)
);

create table if not exists periodic_report_versions (
  id           bigserial primary key,
  tenant_id    uuid not null default app_tenant_id() references tenants(id),
  report_id    uuid not null references periodic_reports(id),
  version      int not null check (version > 0),
  content      jsonb not null,
  author_kind  text not null check (author_kind in ('ai', 'human', 'system')),
  author_id    uuid references user_accounts(id),
  reason       text not null check (length(reason) between 1 and 500),
  lineage      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  unique (report_id, version)
);

-- 21 CFR Part 11-style signature record: who, when, which version, meaning.
create table if not exists report_signoffs (
  id           bigserial primary key,
  tenant_id    uuid not null default app_tenant_id() references tenants(id),
  report_id    uuid not null references periodic_reports(id),
  version      int not null check (version > 0),
  signer_id    uuid not null references user_accounts(id),
  signer_role  text not null,
  meaning      text not null check (length(meaning) between 1 and 300),
  signed_at    timestamptz not null default now(),
  unique (report_id, version)
);

-- ---------------------------------------------------------------------------
-- Audit trail for every case, literature and report action.
-- ---------------------------------------------------------------------------
create table if not exists audit_events (
  id           bigserial primary key,
  tenant_id    uuid not null default app_tenant_id() references tenants(id),
  entity_kind  text not null check (entity_kind in (
    'case', 'literature', 'report', 'product', 'tenant', 'user'
  )),
  entity_ref   text not null,
  event_type   text not null check (length(event_type) between 1 and 64),
  actor_id     uuid references user_accounts(id),
  actor_role   text,
  detail       jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);
create index if not exists audit_events_entity_idx
  on audit_events (tenant_id, entity_kind, entity_ref, created_at desc);
create index if not exists audit_events_recent_idx on audit_events (tenant_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Licensed terminology, loaded per tenant from the tenant's own licensed
-- release. Vyom never ships dictionary content.
-- ---------------------------------------------------------------------------
create table if not exists terminology_terms (
  tenant_id   uuid not null default app_tenant_id() references tenants(id),
  dictionary  text not null,
  llt_code    text not null,
  llt_name    text not null,
  pt_code     text not null,
  pt_name     text not null,
  soc_code    text not null,
  soc_name    text not null,
  primary key (tenant_id, dictionary, llt_code)
);
create index if not exists terminology_terms_name_idx
  on terminology_terms (tenant_id, dictionary, lower(llt_name));

-- Members of the caller's own tenant, readable by the RLS-bound app role.
create or replace view tenant_members as
  select id, tenant_id, email, role, status
  from user_accounts
  where tenant_id = app_tenant_id();

-- ---------------------------------------------------------------------------
-- Append-only guards.
-- ---------------------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'case_versions', 'case_exports', 'literature_outcomes',
    'periodic_report_versions', 'report_signoffs', 'audit_events'
  ] loop
    execute format('drop trigger if exists %I on %I', t || '_append_only', t);
    execute format(
      'create trigger %I before update or delete on %I '
      'for each row execute function reject_ledger_mutation()',
      t || '_append_only', t
    );
  end loop;
end $$;

-- ---------------------------------------------------------------------------
-- Row-level security on every new tenant-scoped table.
-- ---------------------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'products', 'tenant_counters', 'cases', 'case_versions', 'case_exports',
    'literature_outcomes', 'periodic_reports', 'periodic_report_versions',
    'report_signoffs', 'audit_events', 'terminology_terms'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('alter table %I force row level security', t);
    execute format('drop policy if exists tenant_isolation on %I', t);
    execute format(
      'create policy tenant_isolation on %I '
      'using (tenant_id = app_tenant_id()) with check (tenant_id = app_tenant_id())', t
    );
  end loop;
end $$;

grant select, insert on
  case_versions, case_exports, literature_outcomes, periodic_report_versions,
  report_signoffs, audit_events, terminology_terms
  to vyom_app;
grant select, insert, update on products, tenant_counters, cases, periodic_reports to vyom_app;
grant select, insert, update on graph_edges, evidence_spans, awareness_events, case_ready_drafts to vyom_app;
grant select on tenant_members to vyom_app;
grant usage, select on all sequences in schema public to vyom_app;
grant execute on function app_tenant_id() to vyom_app;

-- The service role (sign-in, tenant lookup, seeding, scheduled jobs) bypasses
-- RLS but still needs table privileges. It never runs request-path queries.
grant select, insert, update on all tables in schema public to vyom_service;
grant usage, select on all sequences in schema public to vyom_service;
grant execute on function app_tenant_id() to vyom_service;

-- 005 re-granted every table to vyom_app, which undid 004's revoke. The
-- request role must never read accounts, password hashes, authorization
-- policies, tenant settings or cross-tenant ops tables.
revoke all on table tenants, user_accounts, authorization_policies, ops_alerts, deletion_records from vyom_app;

-- ---------------------------------------------------------------------------
-- Authorization policy for the MVP actions. Deny rows win over allow rows.
-- ---------------------------------------------------------------------------
insert into authorization_policies (role, action, effect, version)
select role, action, effect, 2
from (values
  ('reviewer', 'dashboard.read', 'allow'),
  ('reviewer', 'literature.read', 'allow'),
  ('reviewer', 'literature.screen', 'allow'),
  ('reviewer', 'case.read', 'allow'),
  ('reviewer', 'case.create', 'allow'),
  ('reviewer', 'case.edit', 'allow'),
  ('reviewer', 'case.submit', 'allow'),
  ('reviewer', 'case.assess_causality', 'deny'),
  ('reviewer', 'case.approve', 'deny'),
  ('reviewer', 'report.read', 'allow'),
  ('safety_physician', 'dashboard.read', 'allow'),
  ('safety_physician', 'literature.read', 'allow'),
  ('safety_physician', 'literature.screen', 'allow'),
  ('safety_physician', 'case.read', 'allow'),
  ('safety_physician', 'case.create', 'allow'),
  ('safety_physician', 'case.edit', 'allow'),
  ('safety_physician', 'case.submit', 'allow'),
  ('safety_physician', 'case.assess_causality', 'allow'),
  ('safety_physician', 'case.export', 'allow'),
  ('safety_physician', 'report.read', 'allow'),
  ('safety_physician', 'report.edit', 'allow'),
  ('qppv', 'dashboard.read', 'allow'),
  ('qppv', 'literature.read', 'allow'),
  ('qppv', 'literature.screen', 'allow'),
  ('qppv', 'case.read', 'allow'),
  ('qppv', 'case.export', 'allow'),
  ('qppv', 'report.read', 'allow'),
  ('qppv', 'report.create', 'allow'),
  ('qppv', 'report.edit', 'allow'),
  ('qppv', 'report.signoff', 'allow'),
  ('admin', 'dashboard.read', 'allow'),
  ('admin', 'literature.read', 'allow'),
  ('admin', 'case.read', 'allow'),
  ('admin', 'report.read', 'allow'),
  ('admin', 'product.write', 'allow'),
  ('ops', 'case.read', 'deny'),
  ('ops', 'literature.read', 'deny'),
  ('ops', 'report.read', 'deny')
) as seed(role, action, effect)
where not exists (
  select 1 from authorization_policies existing
  where existing.role = seed.role and existing.action = seed.action and existing.version = 2
);

commit;
