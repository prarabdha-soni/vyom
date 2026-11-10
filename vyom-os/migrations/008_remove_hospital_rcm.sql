-- Stop accepting new hospital RCM domain rows without deleting historical rows.
-- NOT VALID preserves any existing data while enforcing the new domain set on inserts/updates.
begin;

alter table sys1_decisions add column if not exists p_serious_event numeric(5,4)
  check (p_serious_event between 0 and 1);
update sys1_decisions decision
set p_serious_event = decision.p_serious_or_denial
from clinical_states state
where state.id = decision.state_id
  and state.domain in ('pv_literature', 'pv_icsr')
  and decision.p_serious_event is null;

alter table strategies drop constraint if exists strategies_domain_check;
alter table strategies add constraint strategies_domain_check
  check (domain in ('pv_literature', 'pv_icsr')) not valid;

alter table clinical_states drop constraint if exists clinical_states_domain_check;
alter table clinical_states add constraint clinical_states_domain_check
  check (domain in ('pv_literature', 'pv_icsr')) not valid;

alter table capabilities drop constraint if exists capabilities_domain_check;
alter table capabilities add constraint capabilities_domain_check
  check (domain in ('pv_literature', 'pv_icsr')) not valid;

alter table strategies drop constraint if exists strategies_source_check;
alter table strategies add constraint strategies_source_check
  check (source in ('pubmed', 'europepmc', 'partner_e2b', 'safety_email', 'call_transcript', 'hospital_adr_form')) not valid;

alter table source_records drop constraint if exists source_records_source_check;
alter table source_records add constraint source_records_source_check
  check (source in ('pubmed', 'europepmc', 'partner_e2b', 'safety_email', 'call_transcript', 'hospital_adr_form')) not valid;

alter table model_cost_events drop constraint if exists model_cost_events_no_hospital_rcm;
alter table model_cost_events add constraint model_cost_events_no_hospital_rcm
  check (item_type <> 'hospital_rcm') not valid;

commit;