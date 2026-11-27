/**
 * Response shapes from Vyom OS (vyom-os/src/vyom_os). Only the fields the
 * console reads are typed; the API may return more.
 */

import type { Role } from '@/lib/auth/roles';

export type IsoDate = string;
export type IsoDateTime = string;

// ---------------------------------------------------------------------------
// Tenant, user, AI routing
// ---------------------------------------------------------------------------

export type Tenant = {
  readonly id: string;
  readonly slug: string;
  readonly display_name: string;
  readonly kind: string;
  readonly is_fictional: boolean;
  readonly residency_region: string | null;
  readonly hosted_processing_allowed: boolean;
  readonly meddra: { readonly licence_state: string; readonly dictionary: string | null };
  readonly clock_policy: { readonly version: string; readonly serious_days: number; readonly non_serious_days: number };
  readonly auto_close_enabled: boolean;
};

export type ModelRoute = {
  readonly provider: string;
  readonly model_id: string;
  readonly hosted: boolean;
  readonly region: string | null;
};

export const AI_TASKS = [
  'literature_screening',
  'case_extraction',
  'literature_case_extraction',
  'case_narrative',
  'report_drafting',
] as const;
export type AiTask = (typeof AI_TASKS)[number];

export type AiRouting = {
  readonly mode: string;
  readonly is_ai: boolean;
} & { readonly [task in AiTask]?: ModelRoute };

export type Me = {
  readonly user: { readonly id: string; readonly email: string; readonly role: Role };
  readonly tenant: Tenant;
  readonly permissions: readonly string[];
  readonly ai: AiRouting;
  readonly today: IsoDate;
};

export type ActivityRow = {
  readonly entity_kind: string;
  readonly entity_ref: string;
  readonly event_type: string;
  readonly actor_role: string | null;
  readonly actor_email: string | null;
  readonly created_at: IsoDateTime;
};

/** An entity's own history: the same event fields, without the entity, plus detail. */
export type HistoryRow = Omit<ActivityRow, 'entity_kind' | 'entity_ref'> & {
  readonly id: number;
  readonly detail: Record<string, unknown> | null;
};

export type FeedRow = Omit<ActivityRow, 'entity_kind' | 'entity_ref'> & {
  readonly entity_kind?: string;
  readonly entity_ref?: string;
  readonly detail?: Record<string, unknown> | null;
};

// ---------------------------------------------------------------------------
// Literature (Radar)
// ---------------------------------------------------------------------------

export type Band = 'RED_ESCALATE' | 'RED' | 'YELLOW' | 'GREEN_CLOSE' | string;
export type LiteratureOutcome = 'valid_icsr' | 'safety_information' | 'not_relevant' | 'escalated';

export type LiteratureItem = {
  readonly state_id: number;
  readonly title: string;
  readonly first_seen_at: IsoDateTime;
  readonly source: string;
  readonly source_uid: string;
  readonly decision_id: number | null;
  readonly band: Band | null;
  readonly model_id: string | null;
  readonly screened_at: IsoDateTime | null;
  readonly outcome: LiteratureOutcome | null;
  readonly decided_at: IsoDateTime | null;
  readonly case_number: string | null;
  readonly products: readonly string[];
  readonly reference: string;
  readonly journal: string | null;
  readonly pub_date: IsoDate | null;
  readonly is_sample: boolean;
  readonly gates: Record<string, number> | null;
  readonly criteria_met: number | null;
  readonly p_serious: number | null;
  readonly study_design: string | null;
  readonly priority: number | null;
};

export type LiteratureQueue = {
  readonly items: readonly LiteratureItem[];
  readonly counts: Record<string, number>;
};

export type Highlight = { readonly start: number; readonly end: number; readonly kind: string; readonly label: string };

export type ScreeningAnswer = {
  readonly answer?: string;
  readonly choice?: string;
  readonly score?: number;
  readonly probability?: number;
};

export type LiteratureOutcomeRecord = {
  readonly outcome: LiteratureOutcome;
  readonly reason: string | null;
  readonly reviewer_role: string;
  readonly reviewer_email: string;
  readonly created_at: IsoDateTime;
  readonly case_number: string | null;
};

export type LiteratureDetail = {
  readonly state_id: number;
  readonly reference: string;
  readonly citation: string | null;
  readonly title: string;
  readonly abstract: string | null;
  readonly journal: string | null;
  readonly pub_date: IsoDate | null;
  readonly authors: readonly string[];
  readonly pmid: string | null;
  readonly doi: string | null;
  readonly is_sample: boolean;
  readonly first_seen_at: IsoDateTime;
  readonly highlights: {
    readonly title: readonly Highlight[];
    readonly abstract: readonly Highlight[];
    readonly method: string;
  };
  readonly products: readonly string[];
  readonly decision: {
    readonly id: number;
    readonly model_id: string;
    readonly sampler_version: string | null;
    readonly question_schema_version: string | null;
    readonly threshold_policy_version: string | null;
    readonly confidence_band: Band;
    readonly latency_ms: number | null;
    readonly created_at: IsoDateTime;
  } | null;
  readonly summary: {
    readonly gates: Record<string, number> | null;
    readonly criteria_met: number | null;
    readonly p_serious: number | null;
    readonly study_design: string | null;
    readonly priority: number | null;
  } | null;
  readonly questions: readonly { readonly key: string; readonly prompt: string; readonly answer: ScreeningAnswer | null }[];
  readonly is_ai: boolean;
  readonly outcomes: readonly LiteratureOutcomeRecord[];
  /** The decision that closed the article; null while open or escalated. */
  readonly final_outcome: LiteratureOutcomeRecord | null;
  readonly can_decide: boolean;
  /** Escalated and still open: a safety physician decides. */
  readonly awaiting_physician?: boolean;
  readonly history: readonly HistoryRow[];
};

// ---------------------------------------------------------------------------
// Cases (Verify)
// ---------------------------------------------------------------------------

export type CaseStatus = 'data_entry' | 'medical_review' | 'approved' | 'closed_invalid' | 'duplicate';
export type ClockStatus = 'on_track' | 'due_soon' | 'overdue' | 'stopped' | string;

export type Clock = {
  readonly policy_version: string;
  readonly day_zero: IsoDate | null;
  readonly deadline_days: number;
  readonly due_date: IsoDate | null;
  readonly days_elapsed: number | null;
  readonly days_remaining: number | null;
  readonly status: ClockStatus;
  readonly label: string;
};

export type CaseListItem = {
  readonly case_number: string;
  readonly status: CaseStatus;
  readonly source_channel: string;
  readonly serious: boolean;
  readonly day_zero: IsoDate | null;
  readonly current_version: number;
  readonly updated_at: IsoDateTime;
  readonly product_code: string | null;
  readonly first_event: string | null;
  readonly event_count: number;
  readonly valid: boolean;
  readonly expedited_candidate: boolean;
  readonly last_author_kind: string;
  readonly clock: Clock;
};

export type CaseList = { readonly items: readonly CaseListItem[]; readonly counts: Record<string, number> };

export type Evidence = { readonly quote: string; readonly start: number; readonly end: number; readonly status: string };

export type Causality = {
  readonly category: string | null;
  readonly method: string | null;
  readonly comment: string | null;
  readonly assessed_by: string | null;
  readonly assessed_at: IsoDateTime | null;
};

export type Coding = {
  readonly dictionary: string | null;
  readonly soc: string | null;
  readonly pt: string | null;
  readonly pt_code: string | null;
  readonly llt: string | null;
  readonly llt_code: string | null;
  readonly status: string;
};

export type CaseProduct = {
  name: string | null;
  product_code: string | null;
  role: string | null;
  dose: string | null;
  route: string | null;
  indication: string | null;
  start_date: IsoDate | null;
  stop_date: IsoDate | null;
  action_taken: string | null;
};

export type CaseReaction = {
  verbatim: string | null;
  onset_date: IsoDate | null;
  outcome: string | null;
  serious_criteria: string[];
  coding: Coding | null;
  causality: Causality | null;
};

/** The editable case document. Mutable on purpose: edit forms copy and change it. */
export type CasePayload = {
  schema_id: string;
  report_type: string | null;
  patient: {
    initials: string | null;
    age_value: number | null;
    age_unit: string | null;
    age_group: string | null;
    sex: string | null;
    weight_kg: number | null;
    pregnant: boolean | null;
  };
  reporter: { qualification: string | null; country: string | null; identifiable: boolean | null; description: string | null };
  products: CaseProduct[];
  reactions: CaseReaction[];
  special_situations: { kind: string }[];
  medical_history: string[];
  dechallenge: string | null;
  rechallenge: string | null;
  narrative: { text: string | null; status: string | null; citations: string[] } | null;
  literature_reference: string | null;
  evidence: Record<string, Evidence>;
  [key: string]: unknown;
};

export type CaseExport = {
  readonly id: number;
  readonly case_version: number;
  readonly format: string;
  readonly content_sha256: string;
  readonly created_at: IsoDateTime;
  readonly created_by_email: string | null;
};

export type CaseDetail = {
  readonly case: {
    readonly case_number: string;
    readonly status: CaseStatus;
    readonly source_channel: string;
    readonly source_state_id: number | null;
    readonly current_version: number;
    readonly serious: boolean;
    readonly day_zero: IsoDate | null;
    readonly received_at: IsoDateTime | null;
    readonly created_at: IsoDateTime;
    readonly updated_at: IsoDateTime;
    readonly product_code: string | null;
    readonly product_name: string | null;
  };
  readonly version: {
    readonly number: number;
    readonly author_kind: string;
    readonly reason: string | null;
    readonly created_at: IsoDateTime;
    readonly lineage: Record<string, unknown> | null;
  };
  readonly payload: CasePayload;
  readonly assessment: {
    readonly rules_version: string;
    readonly validity: { readonly valid: boolean; readonly criteria: Record<string, boolean>; readonly missing: readonly string[] };
    readonly seriousness: { readonly serious: boolean; readonly criteria: readonly string[] };
    readonly expectedness: readonly { readonly index: number; readonly expected: boolean | null; readonly basis: string }[];
    readonly expedited_candidate: boolean;
    readonly clock: Clock;
    readonly follow_up: { readonly required: boolean; readonly items: readonly string[] };
    readonly causality_complete: boolean;
    readonly reference: { readonly product: string | null; readonly rsi_version: string | null } | null;
  };
  readonly source: {
    readonly channel: string;
    readonly subject: string | null;
    readonly text: string | null;
    readonly literature: { readonly reference?: string; readonly title?: string; readonly citation?: string } | null;
  };
  readonly versions: readonly {
    readonly version: number;
    readonly author_kind: string;
    readonly reason: string | null;
    readonly created_at: IsoDateTime;
    readonly author_email: string | null;
    readonly model_id: string | null;
    readonly is_ai: boolean;
  }[];
  readonly exports: readonly CaseExport[];
  readonly duplicates: readonly {
    readonly case_number: string;
    readonly status: CaseStatus;
    readonly score: number;
    readonly reasons: readonly string[];
    readonly likely: boolean;
  }[];
  readonly similar_reports: readonly unknown[];
  readonly history: readonly HistoryRow[];
  readonly permissions: {
    readonly edit: boolean;
    readonly assess_causality: boolean;
    readonly submit: boolean;
    readonly approve: boolean;
    readonly export: boolean;
  };
  readonly terminology: { readonly licensed: boolean; readonly dictionary: string | null };
};

// ---------------------------------------------------------------------------
// Periodic reports (Dossier)
// ---------------------------------------------------------------------------

export type ReportType = 'pbrer' | 'pader';
export type ReportStatus = 'draft' | 'signed_off';
export type SectionStatus = 'complete' | 'draft' | 'input_required' | 'generated' | string;

export type ReportListItem = {
  readonly report_number: string;
  readonly report_type: ReportType;
  readonly interval_start: IsoDate;
  readonly data_lock_point: IsoDate;
  readonly status: ReportStatus;
  readonly current_version: number;
  readonly updated_at: IsoDateTime;
  readonly product_code: string;
  readonly signed_at: IsoDateTime | null;
  readonly signed_by_email: string | null;
};

export type ReportTable = {
  readonly title: string;
  readonly columns: readonly string[];
  readonly rows: readonly (readonly (string | number | null)[])[];
};

export type ReportSection = {
  readonly key: string;
  readonly mode: 'draft' | 'input' | 'generated' | string;
  readonly text: string | null;
  readonly title: string;
  readonly number: string | number;
  readonly status: SectionStatus;
  readonly tables: readonly ReportTable[];
  readonly lineage: {
    readonly task?: string;
    readonly is_ai?: boolean;
    readonly model_id?: string;
    readonly provider?: string;
    readonly model_version?: string;
    readonly [key: string]: unknown;
  } | null;
  readonly warnings: readonly string[];
  readonly citations: readonly string[];
};

export type ReportStats = Record<string, number>;

export type ReportDetail = {
  readonly report: ReportListItem & {
    readonly created_at: IsoDateTime;
    readonly product_name: string;
    readonly created_by_email: string | null;
  };
  readonly version: number;
  readonly content: {
    readonly data: {
      readonly stats: ReportStats;
      readonly expedited_cases: readonly string[];
      readonly pending_case_numbers: readonly string[];
      readonly lack_of_efficacy_cases: readonly string[];
    };
    readonly schema: string;
    readonly product: {
      readonly code: string;
      readonly name: string;
      readonly rsi_version: string | null;
      readonly active_ingredient: string | null;
      readonly international_birth_date: IsoDate | null;
    };
    readonly interval: { readonly start: IsoDate; readonly data_lock_point: IsoDate };
    readonly sections: readonly ReportSection[];
    readonly report_type: ReportType;
    readonly generated_at: IsoDateTime;
    readonly rules_version: string;
  };
  readonly progress: { readonly total: number; readonly complete: number; readonly draft: number; readonly input_required: number };
  readonly signoff: {
    readonly version: number;
    readonly meaning: string;
    readonly signer_role: string;
    readonly signed_at: IsoDateTime;
    readonly signer_email: string;
  } | null;
  readonly versions: readonly {
    readonly version: number;
    readonly author_kind: string;
    readonly reason: string | null;
    readonly created_at: IsoDateTime;
    readonly author_email: string | null;
  }[];
  readonly history: readonly HistoryRow[];
  readonly permissions: { readonly edit: boolean; readonly signoff: boolean };
  readonly ready_for_signoff: boolean;
  readonly signoff_meaning: string;
};

// ---------------------------------------------------------------------------
// Dashboard, products, settings, ops
// ---------------------------------------------------------------------------

export type ModelCallRow = {
  readonly provider: string;
  readonly model_id: string;
  readonly call_kind: string;
  readonly calls: number;
  readonly failed: number;
  readonly input_tokens: number | null;
  readonly output_tokens: number | null;
};

export type Dashboard = {
  readonly today: IsoDate;
  readonly tenant: Tenant;
  readonly literature: { readonly counts: Record<string, number>; readonly top: readonly LiteratureItem[] };
  readonly cases: {
    readonly counts: Record<string, number>;
    readonly open: number;
    readonly serious_open: number;
    readonly expedited_candidates: number;
    readonly clock: { readonly overdue: number; readonly due_soon: number; readonly on_track: number };
    readonly next_due: readonly CaseListItem[];
  };
  readonly reports: { readonly draft: number; readonly signed_off: number; readonly recent: readonly ReportListItem[] };
  readonly model_calls: readonly ModelCallRow[];
  readonly activity: readonly ActivityRow[];
};

export type Product = {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly active_ingredient: string | null;
  readonly dosage_form: string | null;
  readonly strength: string | null;
  readonly international_birth_date: IsoDate | null;
  readonly reference_safety_terms: readonly { readonly term: string }[];
  readonly rsi_version: string | null;
  readonly active: boolean;
};

export type TenantSettings = {
  readonly tenant: Tenant;
  readonly ai: AiRouting;
  readonly members: readonly { readonly email: string; readonly role: Role; readonly status: string }[];
  readonly permissions: Partial<Record<Role, readonly string[]>>;
  readonly timezone?: string;
};

export type OpsSummary = {
  readonly scope: string;
  readonly ai_mode: string;
  readonly tenants: readonly {
    readonly slug: string;
    readonly display_name: string;
    readonly is_fictional: boolean;
    readonly last_sweep: IsoDateTime | null;
    readonly model_calls_7d: number;
    readonly model_failures_7d: number;
    readonly open_cases: number;
    readonly open_alerts: number;
  }[];
};
