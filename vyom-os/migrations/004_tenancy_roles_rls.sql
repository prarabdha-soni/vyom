-- A1: Tenancy, roles, policy-based authorization, queue jobs, cost telemetry.
-- Append-only rules are preserved for every decision table. RLS is enabled on
-- all tenant-scoped data tables; the service role bypasses RLS only in
-- migrations and batch jobs (never in request handling — enforced by the
-- per-request SET app.tenant_id + role switch in the FastAPI dependency).

begin;

create table if not exists tenants (
  id                    uuid primary key default gen_random_uuid(),
  slug                  text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
  display_name          text not null,
  residency_region      text not null default 'asia-south1',
  meddra_licence_state  text not null default 'none' check (meddra_licence_state in ('none','licensed')),
  hosted_processing_allowed boolean not null default false,
  system_one_routing_policy jsonb not null default '{}'::jsonb,
  auto_close_policy     jsonb not null default '{}'::jsonb,  -- off by default per item type
  feature_flags         jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now()
);

-- Bootstrap tenant used to backfill pre-A1 rows (documented in ADR-003).
insert into tenants (id, slug, display_name)
values ('00000000-0000-0000-0000-000000000001', 'bootstrap', 'Bootstrap tenant')
on conflict do nothing;

create table if not exists user_accounts (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenants(id),
  email           text not null unique check (email = lower(email)),
  password_hash   text not null,                 -- argon2id encoded string
  mfa_secret      text,                          -- encrypted at rest via pgcrypto outside this repo's scope
  mfa_enabled     boolean not null default false,
  role            text not null check (role in (
    'reviewer','safety_physician','qppv','admin','ops'
  )),
  status          text not null default 'active' check (status in ('active','disabled')),
  created_at      timestamptz not null default now(),
  last_login_at   timestamptz
);
create index if not exists user_accounts_tenant_idx on user_accounts (tenant_id);

-- Authorization as data, not scattered ifs. Deny rows win over allow rows.
create table if not exists authorization_policies (
  id          bigserial primary key,
  role        text not null check (role in (
    'reviewer','safety_physician','qppv','admin','ops'
  )),
  action      text not null,          -- e.g. review.accept, case.approve_serious, auto_close.enable
  effect      text not null check (effect in ('allow','deny')),
  condition   jsonb not null default '{}'::jsonb,
  version     int not null default 1,
  created_at  timestamptz not null default now()
);

insert into authorization_policies (role, action, effect) values
  ('reviewer',        'review.read',              'allow'),
  ('reviewer',        'review.correct',           'allow'),
  ('reviewer',        'review.escalate',          'allow'),
  ('reviewer',        'case.approve_serious',     'deny'),
  ('reviewer',        'auto_close.enable',        'deny'),
  ('safety_physician','review.read',              'allow'),
  ('safety_physician','review.correct',           'allow'),
  ('safety_physician','review.escalate',          'allow'),
  ('safety_physician','case.approve',             'allow'),
  ('safety_physician','case.approve_serious',     'allow'),
  ('safety_physician','gold.adjudicate',          'allow'),
  ('safety_physician','auto_close.enable',        'deny'),
  ('qppv',            'review.read',              'allow'),
  ('qppv',            'case.approve',             'allow'),
  ('qppv',            'case.approve_serious',     'allow'),
  ('qppv',            'auto_close.enable',        'allow'),
  ('qppv',            'policy.write',             'allow'),
  ('admin',           'tenant.settings.write',    'allow'),
  ('admin',           'user.manage',              'allow'),
  ('ops',             'ops.read',                 'allow'),
  ('ops',             'case.approve',             'deny'),
  ('ops',             'auto_close.enable',        'deny');

-- Seed labels with a tenant and reviewer linkage (append-only preserved).
alter table human_labels add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table sys1_decisions add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table sys2_syntheses add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table clinical_states add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table source_records add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table strategies add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);
alter table gold_set_labels add column if not exists tenant_id uuid not null
  default '00000000-0000-0000-0000-000000000001' references tenants(id);

-- Dedup identity was global pre-A1; per-tenant it must be scoped.
alter table clinical_states drop constraint if exists clinical_states_domain_dedup_key_key;
alter table clinical_states add constraint clinical_states_tenant_domain_dedup_key
  unique (tenant_id, domain, dedup_key);
alter table strategies drop constraint if exists strategies_domain_target_key_source_version_key;
alter table strategies add constraint strategies_tenant_domain_target_source_version
  unique (tenant_id, domain, target_key, source, version);

-- PostgreSQL-backed queue (existing pattern; SELECT ... FOR UPDATE SKIP LOCKED).
create table if not exists queue_jobs (
  id             bigserial primary key,
  tenant_id      uuid references tenants(id),
  job_type       text not null,               -- literature_sweep | weekly_schedule | benchmark_run
  payload        jsonb not null default '{}'::jsonb,
  status         text not null default 'queued' check (status in ('queued','running','done','failed')),
  attempts       int not null default 0,
  lease_until    timestamptz,
  correlation_id text,
  scheduled_for  timestamptz not null default now(),
  created_at     timestamptz not null default now(),
  finished_at    timestamptz
);
create index if not exists queue_jobs_claim_idx on queue_jobs (status, scheduled_for);

create table if not exists sweep_runs (
  id                bigserial primary key,
  tenant_id         uuid not null references tenants(id),
  run_date          date not null,
  from_date         date not null,
  to_date           date not null,
  status            text not null default 'completed' check (status in ('completed','failed')),
  records_fetched   int not null default 0,
  states_created    int not null default 0,
  decisions_created int not null default 0,
  already_present   int not null default 0,
  strategy_versions jsonb not null default '[]'::jsonb,
  model_versions    jsonb not null default '{}'::jsonb,
  correlation_id    text,
  completed_at      timestamptz not null default now(),
  unique (tenant_id, run_date, from_date, to_date)
);

-- Cost telemetry (A0 rule 10): one append-only row per model call.
create table if not exists model_cost_events (
  id                   bigserial primary key,
  tenant_id            uuid not null references tenants(id),
  item_type            text not null,
  item_ref             text not null,
  provider             text not null,
  model_id             text not null,
  call_kind            text not null check (call_kind in ('system_one','system_two','ocr_page')),
  input_tokens         bigint,               -- NULL when the provider hides usage
  output_tokens        bigint,
  pages                int,
  unit_price_in_per_1k numeric(12,8),
  unit_price_out_per_1k numeric(12,8),
  estimated_cost_usd   numeric(14,8),        -- NULL => unavailable, never fabricated
  latency_ms           int,
  outcome              text not null,
  correlation_id       text not null,
  prompt_version       text not null,
  schema_version       text not null,
  occurred_at          timestamptz not null default now()
);
create index if not exists model_cost_events_tenant_week_idx
  on model_cost_events (tenant_id, occurred_at);

-- Ops alerting (A5): alerts land here so /healthz and monitors can read them.
create table if not exists ops_alerts (
  id           bigserial primary key,
  tenant_id    uuid references tenants(id),
  kind         text not null,      -- sweep_failed | sweep_missed | queue_depth | system_one_outage
  detail       text not null,
  created_at   timestamptz not null default now(),
  acked_at     timestamptz
);

-- ---------------------------------------------------------------------------
-- Row-level security. Tenant-scoped connections set app.tenant_id; the API
-- role has no bypass. Service/migration role may bypass (never request path).
-- ---------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'vyom_app') then
    create role vyom_app login;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'vyom_service') then
    create role vyom_service login bypassrls;
  end if;
end $$;

grant select, insert, update on all tables in schema public to vyom_app;
grant usage, select on all sequences in schema public to vyom_app;

alter table clinical_states enable row level security;
alter table source_records  enable row level security;
alter table sys1_decisions  enable row level security;
alter table sys2_syntheses  enable row level security;
alter table human_labels    enable row level security;
alter table gold_set_labels enable row level security;
alter table strategies      enable row level security;
alter table queue_jobs      enable row level security;
alter table sweep_runs      enable row level security;
alter table model_cost_events enable row level security;

drop policy if exists tenant_isolation_clinical_states on clinical_states;
create policy tenant_isolation_clinical_states on clinical_states
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_source_records on source_records;
create policy tenant_isolation_source_records on source_records
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_sys1 on sys1_decisions;
create policy tenant_isolation_sys1 on sys1_decisions
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_sys2 on sys2_syntheses;
create policy tenant_isolation_sys2 on sys2_syntheses
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_human_labels on human_labels;
create policy tenant_isolation_human_labels on human_labels
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_gold on gold_set_labels;
create policy tenant_isolation_gold on gold_set_labels
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_strategies on strategies;
create policy tenant_isolation_strategies on strategies
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_queue on queue_jobs;
create policy tenant_isolation_queue on queue_jobs
  using (tenant_id is null or current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_sweeps on sweep_runs;
create policy tenant_isolation_sweeps on sweep_runs
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

drop policy if exists tenant_isolation_costs on model_cost_events;
create policy tenant_isolation_costs on model_cost_events
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

-- tenants/user_accounts/authorization_policies/ops_alerts are readable by the
-- service role only; the API resolves them through the service connection and
-- hands tenant-scoped queries to the vyom_app connection.
revoke all on table tenants, user_accounts, authorization_policies, ops_alerts from vyom_app;

commit;
