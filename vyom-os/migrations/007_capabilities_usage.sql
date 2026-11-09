begin;

create table if not exists capabilities (
  id                       bigserial primary key,
  name                     text not null,
  version                  int not null check (version > 0),
  domain                   text not null check (domain in ('pv_literature', 'pv_icsr', 'hospital_rcm')),
  strategy_versions        jsonb not null default '[]'::jsonb,
  gold_set_version         text,
  threshold_policy_version int not null check (threshold_policy_version > 0),
  model_pins               jsonb not null default '{}'::jsonb,
  price_unit               text not null check (price_unit in ('article_screened', 'molecule_month', 'case_completed')),
  status                   text not null default 'draft' check (status in ('draft', 'evaluated', 'approved', 'active')),
  created_at               timestamptz not null default now(),
  unique (name, version)
);

create table if not exists tenant_capabilities (
  tenant_id      uuid not null references tenants(id),
  capability_id  bigint not null references capabilities(id),
  approved_by    uuid references user_accounts(id),
  approved_at    timestamptz,
  created_at     timestamptz not null default now(),
  primary key (tenant_id, capability_id),
  check ((approved_by is null) = (approved_at is null))
);

create table if not exists usage_events (
  id             bigserial primary key,
  tenant_id      uuid not null references tenants(id),
  capability_id  bigint not null references capabilities(id),
  unit           text not null check (unit in ('article_screened', 'molecule_month', 'case_completed')),
  quantity       numeric(14,4) not null check (quantity > 0),
  source_ref     text not null,
  occurred_at    timestamptz not null default now(),
  unique (tenant_id, capability_id, unit, source_ref)
);
create index if not exists usage_events_tenant_time_idx
  on usage_events (tenant_id, occurred_at desc);

drop trigger if exists tenant_capabilities_append_only on tenant_capabilities;
create trigger tenant_capabilities_append_only
  before update or delete on tenant_capabilities
  for each row execute function reject_ledger_mutation();
drop trigger if exists usage_events_append_only on usage_events;
create trigger usage_events_append_only
  before update or delete on usage_events
  for each row execute function reject_ledger_mutation();

alter table tenant_capabilities enable row level security;
alter table tenant_capabilities force row level security;
drop policy if exists tenant_isolation on tenant_capabilities;
create policy tenant_isolation on tenant_capabilities
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

alter table usage_events enable row level security;
alter table usage_events force row level security;
drop policy if exists tenant_isolation on usage_events;
create policy tenant_isolation on usage_events
  using (current_setting('app.tenant_id', true)::uuid = tenant_id)
  with check (current_setting('app.tenant_id', true)::uuid = tenant_id);

grant select on capabilities to vyom_app;
grant select, insert on tenant_capabilities, usage_events to vyom_app;
grant usage, select on sequence usage_events_id_seq to vyom_app;

insert into capabilities (
  name, version, domain, strategy_versions, gold_set_version,
  threshold_policy_version, model_pins, price_unit, status
)
select
  'literature-screening',
  1,
  'pv_literature',
  coalesce((
    select jsonb_agg(
      jsonb_build_object('strategy_id', id, 'target_key', target_key, 'source', source, 'version', version)
      order by id
    )
    from strategies
    where domain = 'pv_literature' and active
  ), '[]'::jsonb),
  null,
  4,
  '{}'::jsonb,
  'article_screened',
  'draft'
on conflict (name, version) do nothing;

commit;