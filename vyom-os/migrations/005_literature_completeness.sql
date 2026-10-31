-- A2: Literature completeness — versioned per-tenant strategies, evidence
-- spans with offsets, awareness dates with rule versions, EMA reference data,
-- uploaded local-journal documents, and the append-only benchmark ledger.

begin;

-- Versioned search strategies gain tenancy + molecule semantics. The old
-- `strategies` table keeps working; these columns make A2 possible.
alter table strategies add column if not exists molecule text;
alter table strategies add column if not exists synonyms jsonb not null default '[]'::jsonb;
alter table strategies add column if not exists salts jsonb not null default '[]'::jsonb;
alter table strategies add column if not exists brand_names jsonb not null default '[]'::jsonb;
alter table strategies add column if not exists created_by uuid references user_accounts(id);
-- Strategy rows are append-only (version changes insert a new row).
drop trigger if exists strategies_append_only on strategies;
create trigger strategies_append_only
  before update or delete on strategies
  for each row execute function reject_ledger_mutation();

-- Weekly schedule configuration per tenant.
create table if not exists sweep_schedules (
  id             bigserial primary key,
  tenant_id      uuid not null references tenants(id) unique,
  weekday        int not null check (weekday between 0 and 6),  -- Monday = 0
  hour_utc       int not null default 2 check (hour_utc between 0 and 23),
  enabled        boolean not null default true,
  last_run_at    timestamptz,
  last_error     text,
  updated_at     timestamptz not null default now()
);

-- Provenance-first logical evidence graph in plain relational tables.
-- Edges carry tenant scope, source reference, provenance class, timestamps.
create table if not exists evidence_spans (
  id             bigserial primary key,
  tenant_id      uuid not null references tenants(id),
  state_id       bigint not null references clinical_states(id),
  kind           text not null,            -- event_verbatim | drug_mention | case_field
  start_char     int not null check (start_char >= 0),
  end_char       int not null check (end_char >= start_char),
  excerpt_hash   char(64) not null,        -- content addressable; excerpt kept in state
  created_at     timestamptz not null default now()
);
create index if not exists evidence_spans_state_idx on evidence_spans (state_id, kind);

create table if not exists graph_edges (
  id              bigserial primary key,
  tenant_id       uuid not null references tenants(id),
  from_kind       text not null,   -- source_record|literature|product|ingredient|manufacturer|batch|case|institution|regulatory_alert
  from_ref        text not null,
  relation        text not null,   -- mentions|contains_ingredient|manufactured_by|supplied_to|used_in_batch|raised_as_case|reported_by|alert_matches
  to_kind         text not null,
  to_ref          text not null,
  evidence_status text not null check (evidence_status in (
    'verified','reported','inferred','unverified','ruled_out'
  )),
  provenance      text not null,   -- deterministic_rule|system_one|system_two|human_label|import
  source_state_id bigint references clinical_states(id),
  created_at      timestamptz not null default now(),
  unique (tenant_id, from_kind, from_ref, relation, to_kind, to_ref, provenance)
);
create index if not exists graph_edges_lookup_idx on graph_edges (tenant_id, to_kind, to_ref);

-- Awareness date when a record first met the four-criteria screen, plus the
-- region/tenant rule version applied (A2).
create table if not exists awareness_events (
  id                bigserial primary key,
  tenant_id         uuid not null references tenants(id),
  state_id          bigint not null references clinical_states(id),
  aware_on          date not null,
  rule_version      text not null,
  region_rule       text not null default 'eu-eea',
  screener_role     text not null,
  created_at        timestamptz not null default now(),
  unique (tenant_id, state_id)
);

-- EMA published substance / journal lists as versioned reference data.
create table if not exists ema_reference_lists (
  id           bigserial primary key,
  list_kind    text not null check (list_kind in ('substance','journal')),
  term         text not null,
  list_version text not null,
  published_on date not null,
  unique (list_kind, term, list_version)
);

create table if not exists ema_reference_matches (
  id             bigserial primary key,
  tenant_id      uuid not null references tenants(id),
  state_id       bigint not null references clinical_states(id),
  reference_id   bigint not null references ema_reference_lists(id),
  matched_on     text not null check (matched_on in ('title','abstract','journal')),
  list_version   text not null,
  flagged_for_review boolean not null default true,  -- never an automatic decision
  created_at     timestamptz not null default now(),
  unique (tenant_id, state_id, reference_id)
);

-- Tenant-uploaded digital local-journal PDFs/issues (text-layer only until C1 OCR).
create table if not exists uploaded_documents (
  id              bigserial primary key,
  tenant_id       uuid not null references tenants(id),
  filename        text not null,
  sha256          char(64) not null check (sha256 ~ '^[0-9a-f]{64}$'),
  page_count      int not null default 0,
  extraction_mode text not null default 'digital_pdf' check (extraction_mode in ('digital_pdf','scanned_manual_review')),
  state_id        bigint references clinical_states(id),
  uploaded_by     uuid references user_accounts(id),
  created_at      timestamptz not null default now(),
  unique (tenant_id, sha256)
);

-- Page/character offsets for extracted upload text (retained per A2).
create table if not exists document_pages (
  id             bigserial primary key,
  document_id    bigint not null references uploaded_documents(id),
  page_number    int not null check (page_number > 0),
  char_start     int not null,
  char_end       int not null,
  unique (document_id, page_number)
);

-- Case-ready drafts: every field linked to a source span (A2).
create table if not exists case_ready_drafts (
  id            bigserial primary key,
  tenant_id     uuid not null references tenants(id),
  state_id      bigint not null references clinical_states(id),
  decision_id   bigint references sys1_decisions(id),
  fields        jsonb not null,          -- {field: {value, span_id}}
  generated_by  text not null,           -- system_two model id
  generated_at  timestamptz not null default now()
);

-- A4: retrospective benchmark against a prospect's historical screening log.
create table if not exists benchmark_records (
  id                 bigserial primary key,
  tenant_id          uuid not null references tenants(id),
  external_uid       text not null,       -- PMID/DOI of prospect-log entry
  screened_on        date not null,
  prospect_decision  text not null check (prospect_decision in ('case_raised','no_case','unclear')),
  case_raised        boolean,
  strategy_version   int,
  raw_row            jsonb not null,
  created_at         timestamptz not null default now(),
  unique (tenant_id, external_uid)
);

create table if not exists benchmark_comparisons (
  id                  bigserial primary key,
  tenant_id           uuid not null references tenants(id),
  benchmark_record_id bigint not null references benchmark_records(id),
  vyom_band           text,
  vyom_decision_id    bigint references sys1_decisions(id),
  agreement           text not null check (agreement in ('agree','disagree')),
  adjudication        text check (adjudication in (
    'confirmed_agree','possible_missed_case','false_alarm','pending'
  )),
  adjudicator_id      uuid references user_accounts(id),
  adjudicated_at      timestamptz,
  evidence_span_ids   jsonb not null default '[]'::jsonb,
  created_at          timestamptz not null default now(),
  unique (tenant_id, benchmark_record_id)
);

create table if not exists benchmark_notifications (
  id                    bigserial primary key,
  tenant_id             uuid not null references tenants(id),
  comparison_id         bigint not null references benchmark_comparisons(id),
  recipient_contact     text not null,
  channel               text not null default 'email_stub',
  message_digest        char(64) not null,
  sent_at               timestamptz not null default now(),
  unique (tenant_id, comparison_id)
);

create table if not exists deletion_records (
  id            bigserial primary key,
  tenant_id     uuid not null references tenants(id),
  requested_by  uuid references user_accounts(id),
  scope         text not null default 'benchmark_tenant',
  rows_removed  jsonb not null default '{}'::jsonb,
  completed_at  timestamptz not null default now()
);

alter table evidence_spans        enable row level security;
alter table graph_edges           enable row level security;
alter table awareness_events      enable row level security;
alter table uploaded_documents    enable row level security;
alter table case_ready_drafts     enable row level security;
alter table benchmark_records     enable row level security;
alter table benchmark_comparisons enable row level security;
alter table benchmark_notifications enable row level security;
alter table ema_reference_matches enable row level security;
alter table sweep_schedules       enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'evidence_spans','graph_edges','awareness_events','uploaded_documents',
    'case_ready_drafts','benchmark_records','benchmark_comparisons',
    'benchmark_notifications','ema_reference_matches','sweep_schedules'
  ] loop
    execute format('create policy tenant_isolation_%I on %I
      using (current_setting(''app.tenant_id'', true)::uuid = tenant_id)
      with check (current_setting(''app.tenant_id'', true)::uuid = tenant_id)', t, t);
  end loop;
end $$;

grant select, insert, update on all tables in schema public to vyom_app;
grant usage, select on all sequences in schema public to vyom_app;

-- EMA reference data is public shared data (clearly historical, rule 14).
insert into ema_reference_lists (list_kind, term, list_version, published_on) values
  ('substance', 'warfarin',   'ema-ref-2026-01', '2026-01-15'),
  ('substance', 'methotrexate','ema-ref-2026-01', '2026-01-15'),
  ('journal',   'Thrombosis Research', 'ema-ref-2026-01', '2026-01-15')
on conflict do nothing;

commit;
