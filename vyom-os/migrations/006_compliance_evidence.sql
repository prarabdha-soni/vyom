-- B1: Compliance evidence — controlled auto-close enablement, release
-- validation packs, and 21 CFR Part 11 alignment records. All decision-ish
-- tables are append-only via the existing reject_ledger_mutation() trigger.

begin;

-- Controlled auto-close enablement (B1). Configuration alone can never turn
-- auto-close on: a QPPV signs this append-only record after reviewing measured
-- recall on adjudicated samples. The deterministic router reads the LATEST
-- row per (tenant, item_type) — enabling requires effect='enabled'; absence or
-- 'disabled' means off (fail-closed default preserved from A1).
create table if not exists auto_close_enablements (
  id                 bigserial primary key,
  tenant_id          uuid not null references tenants(id),
  item_type          text not null,               -- e.g. pv_literature_yellow
  effect             text not null check (effect in ('enabled','disabled')),
  measured_recall    numeric(5,4) check (measured_recall between 0 and 1),
  gold_set_version   text,
  adjudicated_sample_count int not null default 0 check (adjudicated_sample_count >= 0),
  qppv_account_id    uuid not null references user_accounts(id),
  signature_meaning  text not null default 'QPPV approval to enable auto-close for this item type',
  signature_time_source text not null default 'database-clock:now()',
  rationale          text not null,
  correlation_id     text,
  created_at         timestamptz not null default now()
);
create index if not exists auto_close_enablements_lookup
  on auto_close_enablements (tenant_id, item_type, created_at desc);
drop trigger if exists auto_close_enablements_append_only on auto_close_enablements;
create trigger auto_close_enablements_append_only
  before update or delete on auto_close_enablements
  for each row execute function reject_ledger_mutation();

alter table auto_close_enablements enable row level security;
alter table auto_close_enablements force row level security;
drop policy if exists tenant_isolation on auto_close_enablements;
create policy tenant_isolation on auto_close_enablements
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

-- Release validation pack: one row per locked model/prompt release produced
-- automatically by CI on the fixed cadence. Frozen gold-set results, change
-- log, and risk assessment live here so customer QA can review without
-- disconnected manual documents.
create table if not exists release_validation_packs (
  id                  bigserial primary key,
  release_id          text not null unique,        -- e.g. rel-2026q4-001
  released_on         date not null,
  cadence             text not null default 'quarterly',
  pinned_versions     jsonb not null,              -- {model_id, sampler_version, prompt_version, question_schema_version, threshold_policy_version}
  context_of_use_sha256 text not null,             -- hash of the emitted CoU bundle
  gold_set_results    jsonb not null,              -- recall/precision per version tuple
  previous_release_recall numeric(5,4),
  change_log          jsonb not null default '[]'::jsonb,
  risk_assessment     text not null,
  generated_by        text not null default 'ci-release-job',
  created_at          timestamptz not null default now()
);
drop trigger if exists release_packs_append_only on release_validation_packs;
create trigger release_packs_append_only
  before update or delete on release_validation_packs
  for each row execute function reject_ledger_mutation();

-- Documented time source for Part 11 attribution (control statement; the DB
-- clock is the authoritative source used by every ledger table above).
create table if not exists compliance_controls (
  id            bigserial primary key,
  control_ref   text not null unique,   -- e.g. part11-time-source, retention-policy
  description   text not null,
  implemented_in text not null,          -- code/migration reference
  verified_at   timestamptz,
  created_at    timestamptz not null default now()
);
insert into compliance_controls (control_ref, description, implemented_in) values
  ('part11-unique-identities',
   'Unique attributable identities: one account per person, hashed passwords, MFA; every label stores reviewer_id + role.',
   'migrations/004_tenancy_roles_rls.sql (user_accounts, human_labels)'),
  ('part11-signature-meaning',
   'Meaning of signature recorded on approvals: human_labels.action plus auto_close_enablements.signature_meaning.',
   'migrations/002, 006'),
  ('part11-time-source',
   'Documented time source: PostgreSQL now() (timestamptz, UTC) on every append-only ledger row.',
   'all ledger migrations; NTP-managed database host'),
  ('part11-retention',
   'Retention enforced in code: reject_ledger_mutation triggers prevent update/delete of decisions, labels, enablements, and packs.',
   'migrations/002..006 triggers'),
  ('rule9-context-of-use',
   'Every System One question has a versioned context-of-use record; CI gate fails otherwise.',
   'src/vyom_literature/context_of_use.py')
on conflict (control_ref) do nothing;

commit;
