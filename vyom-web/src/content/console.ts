/**
 * Copy for the signed-in console: Dashboard, Radar, Verify, Dossier, Audit,
 * Settings and /ops. Components render this; they never hold copy.
 */

export const consoleShell = {
  nav: [
    { key: 'dashboard', label: 'Dashboard', segment: 'dashboard' },
    { key: 'radar', label: 'Radar', segment: 'radar' },
    { key: 'verify', label: 'Verify', segment: 'verify' },
    { key: 'dossier', label: 'Dossier', segment: 'dossier' },
    { key: 'audit', label: 'Audit', segment: 'audit' },
    { key: 'settings', label: 'Settings', segment: 'settings' },
  ],
  navLabel: 'Workspace',
  menuOpen: 'Open navigation',
  menuClose: 'Close navigation',
  sampleChip: 'SAMPLE DATA',
  roleSwitch: { label: 'Viewing as' },
  userMenu: 'Account',
  signOut: 'Sign out',
  publicSite: 'Public site',
  sampleBanner:
    'Sample workspace. Demo Pharma is a fictional tenant; every product, case and article is invented. Changes are not saved.',
} as const;

/** Shown when a mutation is attempted in the sample workspace. */
export const sampleNotSaved =
  'This is the sample workspace, so nothing was saved. Connect Vyom OS to work on live data.';

export const engineCopy = {
  ruleBased: 'RULE-BASED',
  ai: 'AI',
  ruleBasedLong: 'Rule-based demo engine. Not AI.',
  aiLong: 'AI model',
  modelLabel: 'Model',
} as const;

// ---------------------------------------------------------------------------
// Shared labels
// ---------------------------------------------------------------------------

export const caseStatusLabel: Record<string, string> = {
  data_entry: 'Data entry',
  medical_review: 'Medical review',
  approved: 'Approved',
  closed_invalid: 'Closed · invalid',
  duplicate: 'Duplicate',
};

export const channelLabel: Record<string, string> = {
  safety_email: 'Safety email',
  call_transcript: 'Call transcript',
  manual_entry: 'Manual entry',
  literature: 'Literature',
};

export const bandLabel: Record<string, string> = {
  RED_ESCALATE: 'RED · ESCALATE',
  RED: 'RED',
  YELLOW: 'YELLOW',
  YELLOW_REVIEW: 'YELLOW · REVIEW',
  GREEN: 'GREEN',
  GREEN_CLOSE: 'GREEN · CLOSE',
};

export const literatureOutcomes = [
  {
    value: 'valid_icsr',
    key: 'V',
    label: 'Valid ICSR',
    hint: 'An identifiable patient, reporter, suspect product and event. Opens a case in Verify.',
  },
  {
    value: 'safety_information',
    key: 'S',
    label: 'Safety information',
    hint: 'Relevant to safety but no individual case. Logged for the periodic report.',
  },
  { value: 'not_relevant', key: 'N', label: 'Not relevant', hint: 'No safety content for our products.' },
  { value: 'escalated', key: 'E', label: 'Escalate', hint: 'A safety physician should decide.' },
] as const;

export const outcomeLabel: Record<string, string> = Object.fromEntries(
  literatureOutcomes.map((outcome) => [outcome.value, outcome.label]),
);

/** Section statuses Vyom OS counts as complete. */
export const SECTION_DONE = new Set(['complete', 'accepted', 'edited', 'generated']);

export const sectionStatusLabel: Record<string, string> = {
  complete: 'Complete',
  accepted: 'Accepted',
  edited: 'Written',
  draft: 'Draft',
  input_required: 'Input required',
  generated: 'Generated',
};

export const reportTypeLabel: Record<string, string> = { pbrer: 'PBRER', pader: 'PADER' };
export const reportStatusLabel: Record<string, string> = { draft: 'Draft', signed_off: 'Signed off' };

export const clockStatusLabel: Record<string, string> = {
  on_track: 'On track',
  due_soon: 'Due soon',
  overdue: 'Overdue',
  stopped: 'Clock stopped',
};

/** Activity lines read "<actor> <verb> <entity>". */
export const eventVerb: Record<string, string> = {
  signed_in: 'signed in',
  signed_out: 'signed out',
  case_received: 'received',
  extraction_completed: 'extracted data for',
  case_edited: 'edited',
  narrative_drafted: 'drafted the narrative for',
  case_submit: 'sent to medical review',
  case_return: 'returned to data entry',
  case_approve: 'approved',
  case_close_invalid: 'closed as invalid',
  case_mark_duplicate: 'marked as a duplicate',
  case_reopen: 'reopened',
  causality_assessed: 'assessed causality on',
  possible_duplicate_flagged: 'flagged a possible duplicate of',
  e2b_exported: 'exported E2B for',
  screened_valid_icsr: 'confirmed a valid ICSR in',
  screened_safety_information: 'logged safety information from',
  screened_not_relevant: 'closed as not relevant',
  screened_escalated: 'escalated',
  sweep_completed: 'completed a literature sweep',
  report_created: 'created',
  section_updated: 'updated a section of',
  report_signed_off: 'signed off',
  rsi_updated: 'updated the reference safety information for',
};

export const systemActor = 'Vyom';

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const dashboardCopy = {
  title: 'Dashboard',
  lead: 'Where literature, cases and periodic reports stand today.',
  kpis: {
    literature: { label: 'Articles awaiting a decision', detail: (red: number) => `${red} in the red band` },
    cases: { label: 'Open cases', detail: (serious: number) => `${serious} serious` },
    expedited: { label: 'Expedited candidates', detail: 'Serious and unexpected, open' },
    reports: { label: 'Reports in draft', detail: (signed: number) => `${signed} signed off` },
  },
  literature: {
    heading: 'Literature triage',
    link: 'Open Radar',
    bands: 'Open articles by band',
    decided: 'Decided',
    escalated: 'Escalated to a physician',
    top: 'Next up',
  },
  pipeline: { heading: 'Case pipeline', link: 'Open Verify' },
  clock: {
    heading: 'Reporting clock',
    lead: 'Open cases, earliest due first',
    empty: 'No open cases on the clock.',
    overdue: 'Overdue',
    dueSoon: 'Due soon',
    onTrack: 'On track',
  },
  reports: { heading: 'Periodic reports', link: 'Open Dossier', empty: 'No periodic reports yet.' },
  activity: { heading: 'Recent activity', link: 'Full audit trail', empty: 'Nothing recorded yet.' },
  models: {
    heading: 'Model routing',
    lead: 'Which engine handled each task, and calls in the last seven days',
    calls: 'calls',
    failed: 'failed',
    empty: 'No model calls recorded yet.',
    /** Vyom OS routes short structured calls to a fast model and drafting to a larger one. */
    kind: { system_one: 'Fast model', system_two: 'Drafting model' } as Record<string, string>,
  },
} as const;

export const pipelineStages = [
  { status: 'data_entry', label: 'Data entry' },
  { status: 'medical_review', label: 'Medical review' },
  { status: 'approved', label: 'Approved' },
  { status: 'closed_invalid', label: 'Closed · invalid' },
  { status: 'duplicate', label: 'Duplicate' },
] as const;

export const aiTaskLabel: Record<string, string> = {
  literature_screening: 'Literature screening',
  case_extraction: 'Case extraction',
  literature_case_extraction: 'Literature case extraction',
  case_narrative: 'Case narrative',
  report_drafting: 'Report drafting',
};

// ---------------------------------------------------------------------------
// Radar
// ---------------------------------------------------------------------------

export const radarCopy = {
  title: 'Radar',
  lead: 'Literature screened against your products. Every article gets a human decision.',
  views: [
    { value: 'open', label: 'Open' },
    { value: 'decided', label: 'Decided' },
    { value: 'all', label: 'All' },
  ],
  product: { label: 'Product', all: 'All products', apply: 'Filter' },
  sweep: { label: 'Screen new articles', running: 'Screening…', done: (n: number) => `${n} new articles screened.` },
  columns: ['Article', 'Products', 'Band', 'Criteria', 'Decision'],
  empty: { open: 'Nothing waiting. Every screened article has a decision.', other: 'No articles match.' },
  criteriaMet: (n: number) => `${n} of 4`,
  pending: 'Awaiting decision',
  review: {
    back: 'All articles',
    previous: 'Previous article',
    next: 'Next article',
    shortcuts: 'Keys: J next · K previous · V S N E choose a decision',
    article: 'Article',
    abstract: 'Abstract',
    noAbstract: 'No abstract available.',
    highlightNote: (method: string) => `Highlighted terms: ${method}. Not AI.`,
    screening: 'Screening',
    band: 'Band',
    questions: 'Screening questions',
    probability: 'probability',
    seriousness: 'Probability serious',
    studyDesign: 'Study design',
    decision: 'Your decision',
    suggested: 'SCREEN SUGGESTS',
    reason: 'Reason',
    reasonHint: {
      optional: 'Optional. Recorded in the audit trail.',
      escalated: 'Required. Say what the safety physician should look at.',
      urgent: 'Required. The screen flagged this article as urgent.',
    },
    submit: 'Record decision',
    decided: 'Decision recorded',
    cannotDecide: 'Your role can read this article but not decide it.',
    awaitingPhysician: 'Escalated. A safety physician decides this article.',
    openCase: 'Open case',
    history: 'Activity',
    citation: 'Citation',
    sampleArticle: 'FICTIONAL ARTICLE',
  },
} as const;

// ---------------------------------------------------------------------------
// Verify
// ---------------------------------------------------------------------------

export const verifyCopy = {
  title: 'Verify',
  lead: 'Individual case safety reports from intake to medical review and E2B.',
  views: [
    { value: 'open', label: 'Open' },
    { value: 'medical_review', label: 'Medical review' },
    { value: 'approved', label: 'Approved' },
    { value: '', label: 'All' },
  ],
  newCase: 'New case',
  columns: ['Case', 'Product · event', 'Seriousness', 'Status', 'Clock', 'Updated'],
  empty: 'No cases match.',
  serious: 'SERIOUS',
  nonSerious: 'Non-serious',
  expedited: 'EXPEDITED',
  intake: {
    title: 'New case',
    lead: 'Paste the source as received. Vyom extracts the case and links every field to the words it came from.',
    channel: 'Channel',
    channels: [
      { value: 'safety_email', label: 'Safety email' },
      { value: 'call_transcript', label: 'Call transcript' },
      { value: 'manual_entry', label: 'Manual entry' },
    ],
    subject: 'Subject',
    receivedOn: 'Received on (day zero)',
    sourceText: 'Source text',
    sourceHint: 'Between 20 and 20,000 characters. Use fictional details in a demo.',
    submit: 'Create case',
    cancel: 'Cancel',
    cannot: 'Your role cannot create cases.',
  },
  workspace: {
    back: 'All cases',
    tabs: [
      { value: 'case', label: 'Case' },
      { value: 'source', label: 'Source' },
      { value: 'narrative', label: 'Narrative' },
      { value: 'history', label: 'History' },
    ],
    version: (n: number) => `v${n}`,
    patient: 'Patient',
    reporter: 'Reporter',
    products: 'Products',
    reactions: 'Events',
    special: 'Special situations',
    history: 'Medical history',
    challenge: 'Dechallenge · rechallenge',
    fields: {
      initials: 'Initials',
      age: 'Age',
      ageGroup: 'Age group',
      sex: 'Sex',
      weight: 'Weight (kg)',
      pregnant: 'Pregnant',
      qualification: 'Qualification',
      country: 'Country',
      identifiable: 'Identifiable',
      role: 'Role',
      dose: 'Dose',
      route: 'Route',
      indication: 'Indication',
      dates: 'Start · stop',
      action: 'Action taken',
      verbatim: 'Reported term',
      onset: 'Onset',
      outcome: 'Outcome',
      seriousness: 'Seriousness',
      coding: 'Coding',
      causality: 'Causality (WHO-UMC)',
      expectedness: 'Expectedness',
    },
    evidence: 'Source evidence',
    verified: 'VERIFIED',
    unverified: 'UNVERIFIED',
    noEvidence: 'No source quote',
    notReported: 'Not reported',
    expected: 'Listed',
    unexpected: 'Unlisted',
    codingUnlicensed: 'MedDRA not licensed for this tenant: system organ class only',
    rules: {
      heading: 'Rules',
      validity: 'Minimum criteria',
      criteria: {
        identifiable_patient: 'Identifiable patient',
        identifiable_reporter: 'Identifiable reporter',
        suspect_product: 'Suspect product',
        adverse_event: 'Adverse event',
      } as Record<string, string>,
      seriousness: 'Seriousness',
      expedited: 'Expedited candidate',
      expeditedYes: 'Serious and unlisted: expedited reporting applies',
      expeditedNo: 'Not expedited',
      clock: 'Reporting clock',
      dueOn: 'Due',
      followUp: 'Follow-up',
      followUpNone: 'None needed',
      causality: 'Causality',
      causalityDone: 'Assessed for every event',
      causalityMissing: 'Missing for at least one event',
      reference: 'Reference safety information',
      engine: (version: string) => `Deterministic rules ${version}`,
    },
    duplicates: { heading: 'Possible duplicates', likely: 'LIKELY', score: 'match' },
    versions: 'Versions',
    exports: { heading: 'E2B(R3) exports', create: 'Export E2B', download: 'Download XML', sha: 'SHA-256' },
    transitions: {
      heading: 'Workflow',
      reason: 'Reason',
      duplicateOf: 'Duplicate of (case number)',
      actions: {
        submit: { label: 'Send to medical review', needsReason: false },
        return: { label: 'Return to data entry', needsReason: true },
        approve: { label: 'Approve', needsReason: false },
        close_invalid: { label: 'Close as invalid', needsReason: true },
        mark_duplicate: { label: 'Mark duplicate', needsReason: true },
        reopen: { label: 'Reopen', needsReason: true },
      } as Record<string, { label: string; needsReason: boolean }>,
      approveMeaning: 'Medical review complete. I approve this case version for regulatory reporting.',
      none: 'No workflow actions for your role at this stage.',
    },
    edit: {
      open: 'Edit fields',
      cancel: 'Cancel',
      save: 'Save new version',
      reason: 'Reason for change',
      reasonHint: 'Recorded in the audit trail.',
    },
    causality: {
      heading: 'Record causality',
      category: 'Category',
      comment: 'Comment',
      save: 'Save causality',
      none: 'Not assessed',
      by: 'by',
    },
    narrative: {
      heading: 'Case narrative',
      empty: 'No narrative yet.',
      draft: 'Draft narrative',
      redraft: 'Redraft narrative',
      edit: 'Edit narrative',
      confirm: 'Confirm narrative',
      save: 'Save narrative',
      citations: 'Each sentence is drawn from these source quotes',
      statusLabel: { ai_draft: 'UNREVIEWED DRAFT', edited: 'REVIEWED', empty: 'EMPTY' } as Record<string, string>,
    },
    source: {
      heading: 'Source as received',
      subject: 'Subject',
      literature: 'Literature reference',
      legend: 'Words a case field was verified against',
    },
    nonSeriousChip: 'NON-SERIOUS',
    humanAuthor: 'HUMAN',
    versionColumns: ['Version', 'Author', 'Reason', 'When'],
    activity: 'Activity',
    tabsLabel: 'Case views',
    checksLabel: 'Case checks',
  },
} as const;

export const fieldOptions = {
  sex: ['female', 'male', 'unknown'],
  ageUnit: ['years', 'months', 'weeks', 'days'],
  qualification: ['physician', 'pharmacist', 'other_health_professional', 'lawyer', 'consumer', 'unknown'],
  actionTaken: ['withdrawn', 'dose_reduced', 'dose_increased', 'not_changed', 'unknown', 'not_applicable'],
  outcome: ['recovered', 'recovering', 'not_recovered', 'recovered_with_sequelae', 'fatal', 'unknown'],
  serious: ['death', 'life_threatening', 'hospitalisation', 'disability', 'congenital_anomaly', 'other_medically_important'],
  causality: ['certain', 'probable', 'possible', 'unlikely', 'conditional', 'unassessable'],
} as const;

/** "other_medically_important" → "Other medically important". */
export function humanise(value: string | null | undefined): string {
  if (!value) return '';
  const text = value.replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// ---------------------------------------------------------------------------
// Dossier
// ---------------------------------------------------------------------------

export const dossierCopy = {
  title: 'Dossier',
  lead: 'Periodic safety reports drafted from locked case and literature data, signed off by the QPPV.',
  columns: ['Report', 'Product', 'Interval', 'Progress', 'Status'],
  empty: 'No periodic reports yet.',
  create: {
    heading: 'New periodic report',
    open: 'New report',
    product: 'Product',
    type: 'Report type',
    intervalStart: 'Interval start',
    dataLockPoint: 'Data lock point',
    submit: 'Create draft',
    cannot: 'Only the QPPV creates periodic reports.',
  },
  workspace: {
    back: 'All reports',
    views: [
      { value: 'workflow', label: 'Workflow' },
      { value: 'document', label: 'Document' },
    ],
    viewsLabel: 'Report views',
    stages: {
      lock: 'Data locked',
      drafting: 'Authoring',
      review: 'Ready for sign-off',
      signed: 'Signed off',
    },
    outline: 'Sections',
    progress: (done: number, total: number) => `${done} of ${total} complete`,
    dataPackage: 'Data package',
    stats: {
      interval_cases: 'Cases in interval',
      interval_serious: 'Serious',
      interval_non_serious: 'Non-serious',
      interval_fatal: 'Fatal',
      interval_expedited_candidates: 'Expedited candidates',
      cumulative_cases: 'Cumulative cases',
      pending_cases: 'Still in processing',
      literature_screened: 'Articles screened',
      literature_undecided: 'Articles undecided',
    } as Record<string, string>,
    dlp: 'DLP',
    locked: 'LOCKED',
    interval: 'Interval',
    cited: (n: number) => `${n} CITED`,
    roles: { author: 'Author', reviewer: 'Reviewer', approver: 'Approver' },
    roleNames: {
      rules: 'Vyom rules engine',
      ai: 'Vyom AI draft',
      input: 'Marketing authorisation holder',
      reviewer: 'Safety physician',
      approver: 'QPPV',
    },
    mode: { draft: 'DRAFTED', input: 'INPUT', generated: 'GENERATED' } as Record<string, string>,
    guidance: 'Regulatory guidance',
    guidanceSource: (type: string) => (type === 'pader' ? '21 CFR 314.80 · PARAPHRASED' : 'ICH E2C(R2) · PARAPHRASED'),
    activity: 'Activity record',
    noActivity: 'No changes to this section yet.',
    warnings: 'Check before sign-off',
    empty: 'This section needs input before sign-off.',
    edit: 'Edit section',
    accept: 'Accept draft',
    save: 'Save section',
    cancel: 'Cancel',
    reason: 'Reason',
    text: 'Section text',
    provenance: 'Provenance',
    comments: 'Comments',
    lineage: {
      task: 'Task',
      engine: 'Engine',
      model: 'Model',
      rules: 'Rules version',
      generated: 'Data drawn',
      version: 'Report version',
      citations: 'Cited records',
      noCitations: 'This section cites no individual records.',
      human: 'Written by a person. No model involved.',
      assembled: 'Assembled by the rule-based engine from case and literature records. No model involved.',
      awaiting: 'Nothing written yet. This section waits for input from the marketing authorisation holder.',
    },
    commentsSample: 'Sample comments, for the demo. Comments are not stored by Vyom OS yet.',
    commentsLive: 'Section comments are not stored by Vyom OS yet. Use the reason on each change.',
    signoff: {
      heading: 'QPPV sign-off',
      notReady: (left: number) => `${left} section${left === 1 ? '' : 's'} still need input or acceptance.`,
      ready: 'Every section is complete. The QPPV can sign off.',
      password: 'Your password',
      passwordHint: 'Re-enter your password to sign. This is recorded with the meaning below.',
      submit: 'Sign off report',
      signed: 'Signed off',
      by: 'by',
      locked: 'Signed-off reports cannot change. Create a new report for a later interval.',
      notQppv: 'Only the QPPV signs off periodic reports.',
    },
    export: 'Export Markdown',
  },
} as const;

/** Short, paraphrased reminders of what each section should contain. */
export const sectionGuidance: Record<string, string> = {
  introduction:
    'Name the product, the reporting interval and its place in the sequence of reports, and say briefly what the report covers.',
  approval_status:
    'Summarise where the product is approved, when it was first approved anywhere, and any approvals, refusals or withdrawals in the interval.',
  safety_actions:
    'Describe significant actions taken for safety reasons in the interval by the company or any authority, and why.',
  rsi_changes:
    'List changes made to the reference safety information during the interval, and name the version used for this report.',
  exposure:
    'Estimate cumulative exposure in clinical trials and interval exposure after marketing, with the method and its limits.',
  summary_tabulations:
    'Give interval and cumulative tabulations of serious adverse events from trials and of reports from post-marketing sources.',
  clinical_trials:
    'Summarise clinically important safety findings that emerged from company-sponsored interventional trials in the interval.',
  non_interventional: 'Summarise relevant safety information from non-interventional studies completed or ongoing in the interval.',
  other_sources: 'Summarise safety information from other trials and sources, such as pooled analyses or investigator-led studies.',
  non_clinical: 'Summarise major safety findings from non-clinical studies completed in the interval.',
  literature:
    'Summarise new and significant safety findings published in the interval, including relevant information on related substances.',
  other_periodic_reports:
    'Mention other periodic reports prepared for the same product in the interval, only where they hold significant findings.',
  lack_of_efficacy:
    'Summarise data showing lack of efficacy in controlled trials for treatments of serious or life-threatening conditions.',
  late_breaking:
    'Summarise significant safety information that arrived after the data lock point while the report was being prepared.',
  signals_overview: 'List signals that were new, ongoing or closed during the interval, with their status.',
  signal_risk_evaluation:
    'Evaluate the signals closed in the interval and any new information on important identified and potential risks.',
  benefit_evaluation: 'Summarise important efficacy and effectiveness information that supports the benefit side of the analysis.',
  benefit_risk: 'Weigh benefits against risks for the approved indications, and explain the reasoning.',
  conclusions:
    'State whether the benefit-risk balance has changed and what actions, such as label changes, are proposed as a result.',
  appendices: 'Attach the reference safety information, line listings and other supporting tables.',
  pader_narrative:
    'Give a narrative summary and analysis of the reports in the interval, with the case line listing referenced.',
  pader_actions: 'Describe actions taken since the last report because of adverse experiences, such as labelling changes.',
  pader_listing: 'Attach the line listing of the serious and non-serious reports included in this periodic report.',
};

/**
 * Sample-only discussion for the demo, keyed by report and section. These are
 * fictional and never shown for a live tenant.
 */
export const sampleComments: Record<string, readonly { author: string; role: string; body: string; when: string }[]> = {
  'VY-PBRER-0001/summary_tabulations': [
    {
      author: 'physician@demo-pharma.example',
      role: 'Safety physician',
      body: 'Counts match the approved line listing. The four cases still in processing are noted in the text, which is what we want.',
      when: 'Today',
    },
  ],
  'VY-PBRER-0001/literature': [
    {
      author: 'qppv@demo-pharma.example',
      role: 'QPPV',
      body: 'Hold this until the lack-of-efficacy article for VY-201 has a decision in Radar; it may need a mention here.',
      when: 'Today',
    },
    {
      author: 'reviewer@demo-pharma.example',
      role: 'PV reviewer',
      body: 'Noted. It is next in my queue.',
      when: 'Today',
    },
  ],
  'VY-PBRER-0001/conclusions': [
    {
      author: 'qppv@demo-pharma.example',
      role: 'QPPV',
      body: 'Draft conclusion is fine as a starting point. I will finalise after the signal sections are in.',
      when: 'Today',
    },
  ],
};

// ---------------------------------------------------------------------------
// Audit, settings, ops
// ---------------------------------------------------------------------------

export const auditCopy = {
  title: 'Audit',
  lead: 'Every change, decision and sign-off, newest first. Records cannot be edited or deleted.',
  filters: [
    { value: '', label: 'All' },
    { value: 'literature', label: 'Literature' },
    { value: 'case', label: 'Cases' },
    { value: 'report', label: 'Reports' },
    { value: 'product', label: 'Products' },
    { value: 'user', label: 'Sign-ins' },
  ],
  columns: ['When', 'Who', 'What', 'Record'],
  empty: 'No records match.',
  limit: 'Showing the 100 most recent records.',
} as const;

export const settingsCopy = {
  title: 'Settings',
  lead: 'How this tenant is set up. Changes are made by Vyom operations during onboarding.',
  tenant: {
    heading: 'Tenant',
    name: 'Name',
    slug: 'Workspace address',
    kind: 'Type',
    region: 'Data residency',
    hosted: 'Hosted model processing',
    allowed: 'Allowed',
    notAllowed: 'Not allowed',
    autoClose: 'Automatic closing of green-band articles',
    on: 'On',
    off: 'Off',
  },
  clock: { heading: 'Reporting clock', serious: 'Serious cases', nonSerious: 'Non-serious cases', days: 'days', policy: 'Policy' },
  meddra: { heading: 'Terminology', licence: 'MedDRA licence', dictionary: 'Dictionary', none: 'Not licensed' },
  ai: { heading: 'Model routing', task: 'Task', engine: 'Engine', region: 'Region', local: 'Local' },
  products: {
    heading: 'Products',
    code: 'Code',
    form: 'Form · strength',
    ibd: 'International birth date',
    rsi: 'Reference safety information',
    terms: 'listed terms',
  },
  members: { heading: 'Members', email: 'Email', role: 'Role', status: 'Status' },
  permissions: { heading: 'Role permissions', lead: 'What each role may do. Enforced by Vyom OS on every request.' },
} as const;

export const opsCopy = {
  title: 'Operations',
  lead: 'Every tenant at a glance, for Vyom staff. No case content is shown here.',
  columns: ['Tenant', 'Last literature sweep', 'Model calls (7 days)', 'Failures', 'Open cases'],
  never: 'Never',
  scope: 'Scope',
  aiMode: 'Model mode',
} as const;

export const loginCopy = {
  eyebrow: 'SIGN IN',
  heading: 'Sign in to Vyom',
  lead: 'Use the work email and password your administrator set up for you.',
  email: 'Work email',
  password: 'Password',
  submit: 'Sign in',
  pending: 'Signing in…',
  expired: 'Your session ended. Sign in again.',
  notConfigured: 'Live sign-in is not configured for this deployment yet.',
  signedInAs: (email: string) => `You are signed in as ${email}.`,
  continue: 'Continue to your workspace',
  sample: {
    eyebrow: 'SAMPLE WORKSPACE',
    heading: 'Explore with sample data',
    lead: 'Open Demo Pharma, a fictional tenant with invented products, cases and articles. Pick a role to see what it can do. Nothing you change is saved.',
    roles: [
      { value: 'reviewer', label: 'PV reviewer', hint: 'Screens literature and processes cases' },
      { value: 'safety_physician', label: 'Safety physician', hint: 'Medical review, causality and E2B' },
      { value: 'qppv', label: 'QPPV', hint: 'Periodic reports and sign-off' },
      { value: 'admin', label: 'Tenant admin', hint: 'Settings and members' },
      { value: 'ops', label: 'Vyom operations', hint: 'Cross-tenant health' },
    ],
    submit: 'Open as',
  },
  home: 'Back to the public site',
} as const;
