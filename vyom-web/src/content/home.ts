/**
 * Home page copy, in the order the design presents it.
 *
 * Every number here is one of three things: a sourced market fact, a labelled
 * target, or sample data shown behind a SAMPLE DATA chip.
 */

export const homeMeta = {
  title: 'Vyom — The operating system for modern drug safety and quality',
  description:
    'The operating system for modern drug safety and quality. Connect fragmented evidence and workflows with traceable review across literature, cases and product-quality concerns.',
} as const;

export const hero = {
  pill: 'AI-NATIVE DRUG SAFETY & QUALITY',
  /**
   * One sentence that wraps naturally. Split so `highlight` can take the
   * accent colour and the underline without the component hardcoding the
   * phrase — change the wording here and the emphasis follows.
   */
  headline: {
    before: 'The operating system for ',
    highlight: 'modern drug safety and quality',
    after: '.',
  },
  subline:
    'Turn fragmented safety data and manual workflows into connected, intelligent and traceable safety operations.',
  primaryCta: { label: 'Book a Demo', href: '/book-demo' },
  secondaryCta: { label: 'Explore the Platform', href: '/platform' },
  footnote: 'Vyom connects and checks the evidence. Qualified people review it and decide.',
} as const;

/** The headline as one string, for metadata and anywhere plain text is needed. */
export const heroHeadlineText = `${hero.headline.before}${hero.headline.highlight}${hero.headline.after}`;

/**
 * The hero workspace preview. Sample data, fictional identifiers only — no
 * lot numbers, because CLAUDE.md allows none, and a missing lot is itself
 * the evidence gap the panel demonstrates.
 */
export const workspacePreview = {
  title: 'Safety workspace',
  subtitle: 'DEMO-HOSPITAL (FICTIONAL)',
  incoming: {
    label: 'INCOMING REPORTS · TODAY',
    rows: [
      { id: 'VY-CASE-0417', source: 'Hospital pharmacy note', status: 'POSSIBLE DUPLICATE', tone: 'accent' },
      { id: 'VY-CASE-0416', source: 'Literature article', status: 'FIELDS EXTRACTED', tone: 'accent' },
      { id: 'VY-CASE-0415', source: 'Partner E2B file', status: 'QUEUED', tone: 'default' },
    ],
  },
  case: {
    label: 'SAFETY CASE',
    id: 'VY-CASE-0412',
    title: 'Suspected lack of effect after VY-305 injection',
    /**
     * `state` drives the marker: `linked` fields show their source, `conflict`
     * and `missing` are flagged for a person to resolve.
     */
    fields: [
      { label: 'PRODUCT', value: 'VY-305 injection', source: 'Pharmacy log', state: 'linked' },
      { label: 'EVENT', value: 'Expected effect not observed', source: 'Clinical note', state: 'linked' },
      { label: 'REPORTER', value: 'Treating physician', source: 'Intake form', state: 'linked' },
      { label: 'ADMINISTERED', value: 'Two different dates recorded', source: 'Conflict', state: 'conflict' },
      { label: 'BATCH / LOT', value: 'Not in any linked record', source: 'Missing', state: 'missing' },
    ],
    evidence: '4 source passages linked',
    review: { label: 'Physician review', detail: 'Waiting · evidence attached' },
  },
  alert: {
    label: 'PRODUCT-QUALITY ALERT',
    title: 'VY-305 appears in one other case this week',
    body: 'Neither case records a lot number, so a batch relationship is not established.',
    status: 'POTENTIAL LINK — UNVERIFIED',
  },
  timeline: {
    label: 'AUDIT TIMELINE',
    /** `ai` = blue, `human` = amber, `system` = neutral, `next` = not yet reached. */
    steps: [
      { time: '09:02', name: 'Received', detail: 'Pharmacy note ingested', actor: 'system' },
      { time: '09:03', name: 'Extracted', detail: 'Fields linked to 4 passages', actor: 'ai' },
      { time: '09:03', name: 'Validated', detail: '1 conflict, 1 missing field', actor: 'ai' },
      { time: '09:04', name: 'Connected', detail: 'Related VY-305 case surfaced', actor: 'ai' },
      { time: 'NOW', name: 'Physician review', detail: 'Waiting on a decision', actor: 'human' },
      { time: 'NEXT', name: 'Decision recorded', detail: 'Reason and version kept', actor: 'next' },
    ],
  },
  footer: ['EVERY FIELD LINKS TO ITS SOURCE', 'AI PROPOSES · PHYSICIAN DECIDES'],
} as const;

/** The hero case-run panel. Sample data, fictional identifiers only. */
export const caseRun = {
  title: 'Case run',
  caseId: 'VY-CASE-0412',
  chips: [
    { label: 'SOURCE · LITERATURE', tone: 'default' },
    { label: 'SUSPECT DRUG · VY-201', tone: 'default' },
    { label: 'SERIOUS · DAY 3 OF 15', tone: 'amber' },
  ],
  passage: {
    label: 'SOURCE PASSAGE · JOURNAL ARTICLE',
    /** Segments render as plain text or as an accent/amber highlight. */
    segments: [
      { text: '“A ', mark: null },
      { text: '54-year-old woman', mark: 'accent' },
      { text: ' developed ', mark: null },
      { text: 'elevated liver enzymes', mark: 'accent' },
      { text: ' and was ', mark: null },
      { text: 'hospitalised', mark: 'amber' },
      { text: ' two weeks after starting ', mark: null },
      { text: 'VY-201', mark: 'accent' },
      { text: '.”', mark: null },
    ],
    note: 'Every extracted field links back to the words it came from.',
  },
  steps: [
    { name: 'Intake', detail: 'Article ingested · no duplicate found', time: '09:02:11', state: 'done' },
    { name: 'Validity', detail: 'Patient, reporter, drug and event identified', time: '09:02:14', state: 'done' },
    { name: 'Coding', detail: 'MedDRA PT Hepatotoxicity · confidence 0.94', time: '09:02:19', state: 'done' },
    { name: 'Seriousness', detail: 'Hospitalisation · unlisted for VY-201', time: '09:02:23', state: 'done' },
    { name: 'Narrative', detail: 'Draft written with 4 cited passages', time: '09:02:41', state: 'done' },
    { name: 'Physician review', detail: 'Waiting · evidence attached', time: 'NOW', state: 'waiting' },
    { name: 'E2B(R3) report', detail: 'Due 24 Oct · 12 days left', time: 'NEXT', state: 'next' },
  ],
  actions: ['Approve', 'Correct', 'Escalate'],
  actionNote: 'AI PROPOSES · PHYSICIAN DECIDES',
} as const;

export const caseRunPills = [
  { name: 'Validity', primitive: 'NOUL · 0.98', detail: 'Patient, reporter, drug and event' },
  { name: 'Event', primitive: 'CHOICE · 0.94', detail: 'elevated liver enzymes (verbatim)' },
  { name: 'Seriousness', primitive: 'NOUL · 0.97', detail: 'Hospitalisation · physician review' },
  { name: 'Timeline', primitive: 'SCORE · 4/5', detail: '15-Day Expedited' },
] as const;

export const standards = {
  label: 'DESIGNED FOR',
  ariaLabel: 'Standards Vyom is designed for',
  items: [
    'ICH E2B(R3)',
    'MedDRA',
    'WHODrug',
    'EU GVP Module VI',
    'US 21 CFR 314.80',
    'CDSCO · PvPI',
    'CIOMS AI in PV',
    'India DPDP Act',
  ],
} as const;

export const problem = {
  eyebrow: 'THE PROBLEM',
  heading: 'Patient safety should not depend on fragmented workflows.',
  lead: 'Safety teams spend much of their time moving information between systems instead of assessing it.',
  statement:
    'Vyom connects the evidence once, keeps every link traceable, and leaves the decisions to qualified people.',
  items: [
    {
      icon: 'inbox',
      title: 'Scattered sources',
      body: 'Safety information sits in emails, documents, literature, spreadsheets and systems that do not talk to each other.',
    },
    {
      icon: 'pencil',
      title: 'Manual intake',
      body: 'Case intake, transcription, duplicate checks and medical coding are still largely done by hand.',
    },
    {
      icon: 'repeat',
      title: 'Repeated checks',
      body: 'The same completeness and quality checks are run again at every hand-off.',
    },
    {
      icon: 'unlink',
      title: 'Disconnected records',
      body: 'Clinical, pharmacy, regulatory and distribution records live apart, so every link is rebuilt by hand.',
    },
    {
      icon: 'clock',
      title: 'Timelines rebuilt from scratch',
      body: 'Working out which product and batch reached which patient, and when, means slow document-by-document reconstruction.',
    },
    {
      icon: 'pin',
      title: 'Limited visibility',
      body: 'When a product-quality concern is reported in one place, it is hard to tell whether it needs investigating elsewhere.',
    },
  ],
  statsLabel: 'CONTEXT · SOURCED MARKET FACTS',
  /** Sourced market facts. The source is shown under each. */
  stats: [
    { value: '40–85%', label: 'of drug-safety budgets go to case processing.', source: 'SOURCE · DELOITTE' },
    { value: '10–15%', label: 'growth in case volumes, every year.', source: 'SOURCE · DELOITTE' },
    { value: '1M+', label: 'adverse-event reports reach the US FDA each year.', source: 'SOURCE · US FDA' },
    { value: '47%', label: 'of US generic prescriptions are supplied by India.', source: 'SOURCE · GTRI' },
  ],
} as const;

export const productsSection = {
  eyebrow: 'PRODUCTS',
  heading: 'One safety system. Six products.',
  lead: 'Start with one workflow and add the rest as trust grows. Every product shares the same agents, rules and evidence trail.',
  osCta: { label: 'Talk to us about licensing', href: '/contact' },
  cards: [
    {
      name: 'Vyom Cases',
      description: 'End-to-end adverse event intake to E2B(R3)',
      icon: 'cases',
      badge: null,
    },
    {
      name: 'Vyom Literature',
      description: 'Weekly medical journal screening',
      icon: 'literature',
      badge: null,
    },
    {
      name: 'Vyom Audit',
      description: 'Independent QA across any vendor’s safety cases',
      icon: 'audit',
      badge: '100% · DESIGN TARGET',
    },
    {
      name: 'Vyom Reports',
      description: 'Periodic safety reports drafted from your data',
      icon: 'reports',
      badge: 'ROADMAP',
    },
    {
      name: 'Vyom Signal',
      description: 'Emerging risks surfaced earlier',
      icon: 'signal',
      badge: 'ROADMAP',
    },
    {
      name: 'Vyom OS',
      description: 'Self-hosted System One decision engine for safety teams',
      icon: 'os',
      badge: 'ROADMAP',
    },
  ] as const,
} as const;

/** Sample data for the flagship card's queue. */
export const caseQueue = {
  label: 'CASE QUEUE · TODAY',
  rows: [
    { id: 'VY-CASE-0412', detail: 'Literature · serious', status: 'AWAITING PHYSICIAN', tone: 'amber' },
    { id: 'VY-CASE-0415', detail: 'Partner E2B file · non-serious', status: 'READY TO SUBMIT', tone: 'accent' },
    { id: 'VY-CASE-0414', detail: 'Call-centre note · serious', status: 'ESCALATED · LOW CONFIDENCE', tone: 'amber' },
  ],
} as const;

/** Sample data for the literature card's funnel. */
export const literatureFunnel = {
  label: 'ONE WEEK',
  rows: [
    { label: 'Articles retrieved', value: '4,820', width: 100, tone: 'muted' },
    { label: 'Unique after de-duplication', value: '3,910', width: 81, tone: 'muted' },
    { label: 'Flagged by AI for review', value: '212', width: 4.4, tone: 'accent' },
    { label: 'Valid cases confirmed', value: '41', width: 0.9, tone: 'amber' },
  ],
} as const;

/**
 * The six platform modules. Status is never written here: a module that maps
 * to a product takes that product's status from `products.ts`, so the two can
 * never disagree. Live Safety Intelligence has no product yet and is roadmap.
 */
export const platformModules = {
  eyebrow: 'PLATFORM',
  heading: 'One intelligent system across the safety lifecycle.',
  lead: 'Six modules share one evidence model, so a record linked at intake is the same record that is reviewed, reported and audited. Each card shows where the module stands today.',
  productLinkPrefix: 'Part of',
  modules: [
    {
      icon: 'intake',
      name: 'Intelligent Safety Intake',
      points: [
        'Ingest information from supported sources',
        'Extract relevant details',
        'Identify potential duplicates',
        'Route records for review',
      ],
      product: 'cases',
      featured: false,
    },
    {
      icon: 'cases',
      name: 'Structured Case Intelligence',
      points: [
        'Organise patient, product, event, reporter and supporting evidence',
        'Highlight missing fields and conflicting information',
        'Preserve source links',
      ],
      product: 'cases',
      featured: false,
    },
    {
      icon: 'reports',
      name: 'Regulatory Documentation',
      points: [
        'Assist with drafting and validating safety documentation',
        'Support configured regional requirements',
        'Keep human review and submission authorisation explicit',
      ],
      product: 'reports',
      featured: false,
    },
    {
      icon: 'network',
      name: 'Live Safety Intelligence',
      points: [
        'Explore public drug-quality alerts and historical safety incidents',
        'Connect product and batch information to documented distribution records',
        'Investigate potential geographic spread',
        'Compare reports across locations and timelines',
        'Identify evidence gaps and unresolved questions',
      ],
      product: null,
      featured: true,
    },
    {
      icon: 'signal',
      name: 'Signal Intelligence',
      points: [
        'Surface potential patterns across cases, products and locations',
        'Show supporting evidence and uncertainty',
        'Distinguish statistical associations from established causality',
      ],
      product: 'signal',
      featured: false,
    },
    {
      icon: 'audit',
      name: 'Quality & Audit',
      points: [
        'Track validation findings, review history, regulatory timelines and open quality issues',
        'Preserve traceable changes and approval records',
      ],
      product: 'audit',
      featured: false,
    },
  ],
  /** Live Safety Intelligence has no product page; it opens the preview instead. */
  intelligenceLink: { label: 'Open the preview', href: '/intelligence' },
} as const;

export const howItWorks = {
  eyebrow: 'HOW IT WORKS',
  heading: 'Intelligence connected by evidence. Controlled by experts.',
  lead: 'Four connected steps. Select a step to see what Vyom does, what people decide, and what the record keeps.',
  columns: { vyom: 'VYOM', people: 'PEOPLE', record: 'THE RECORD KEEPS' },
  /** `tone` follows the colour rule: accent = AI activity, amber = a human decision. */
  steps: [
    {
      index: '01 · SYSTEM',
      title: 'Ingest',
      summary: 'Bring supported safety information into a structured workflow.',
      tone: 'default',
      vyom: [
        'Accepts supported sources such as email, PDFs, literature and partner files',
        'Records where and when each item arrived',
      ],
      people: ['Choose which sources are connected and who may see them'],
      record: 'The original file, its arrival time and its source reference.',
    },
    {
      index: '02 · AI',
      title: 'Connect',
      summary: 'Link relevant product, batch, distribution, clinical and source records.',
      tone: 'accent',
      vyom: [
        'Proposes links between product, batch, distribution, clinical and source records',
        'Shows the passage or document behind every proposed link',
      ],
      people: ['Accept, correct or reject each proposed link'],
      record: 'Each link, its source, and whether it is verified, reported or inferred.',
    },
    {
      index: '03 · AI + RULES',
      title: 'Validate',
      summary: 'Highlight missing information, inconsistencies, duplicates and uncertain relationships.',
      tone: 'accent',
      vyom: [
        'Flags missing fields, conflicting values and possible duplicates',
        'Marks any relationship it cannot confirm as unverified',
      ],
      people: ['Resolve each flag or send it back for follow-up'],
      record: 'Every flag, who resolved it, and how.',
    },
    {
      index: '04 · EXPERTS',
      title: 'Review & Act',
      summary: 'Authorised professionals assess the evidence, approve actions and document decisions.',
      tone: 'amber',
      vyom: ['Assembles the evidence side by side for the reviewer'],
      people: [
        'Assess the evidence and decide',
        'Approve or reject any action, with a recorded reason',
      ],
      record: 'The decision, the reviewer, the time, the reason and the version.',
    },
  ],
} as const;

export const whyAiNative = {
  eyebrow: 'WHY AI-NATIVE',
  heading: 'Built around the safety workflow, not bolted onto it.',
  lead: 'AI added to an old workflow speeds up one step and leaves the gaps between steps. Vyom is designed so that every step shares the same records, checks and history.',
  points: [
    { title: 'Context-aware processing', body: 'Each step works on the connected records, not an isolated form.' },
    { title: 'Traceable outputs', body: 'Every generated field, summary or draft links back to the source evidence.' },
    { title: 'Continuous validation', body: 'Checks run throughout the workflow, not only at the end.' },
    { title: 'Human review and override', body: 'People can correct or override any output, and the correction is kept.' },
    { title: 'Explainable findings', body: 'Findings show their evidence and uncertainty, with a versioned audit history.' },
    { title: 'Configurable controls', body: 'Thresholds, approvals and access are set per organisation for regulated work.' },
  ],
} as const;

export const trust = {
  eyebrow: 'ENTERPRISE TRUST',
  heading: 'Designed for accountable safety operations.',
  lead: 'Controls are part of the design, so each organisation can validate Vyom against its own requirements.',
  items: [
    { icon: 'link', title: 'Evidence-linked outputs', body: 'Every output points to the records and passages behind it.' },
    { icon: 'users', title: 'Role-based permissions', body: 'Access is granted by role and need, for each organisation.' },
    { icon: 'list', title: 'Traceable changes', body: 'Who changed what, when and why, with full review history.' },
    { icon: 'sliders', title: 'Configurable workflows', body: 'Validation rules and approval steps are set by your quality team.' },
    { icon: 'lock', title: 'Data protection', body: 'Isolated, encrypted data for each customer, with controlled access.' },
    { icon: 'shield', title: 'Validation support', body: 'Built to support customer validation and applicable regulatory requirements.' },
  ],
  footnote: 'DESIGN PRINCIPLES · NOT CERTIFICATIONS',
} as const;

export const platformSection = {
  eyebrow: 'PLATFORM',
  heading: 'AI proposes. Rules check. Experts decide.',
  lead: 'Every step leaves evidence. No case is excluded by AI alone until its accuracy on your data meets a threshold your qualified person has approved.',
  steps: [
    { index: '01 · SYSTEM', title: 'Ingest', body: 'Email, PDFs, literature, call-centre notes and partner E2B files, de-duplicated on arrival.', tone: 'default' },
    { index: '02 · AI AGENTS', title: 'Understand', body: 'Agents extract patient, drug, event and seriousness, quoting the exact source passage.', tone: 'accent' },
    { index: '03 · RULES', title: 'Check', body: 'Deterministic rules confirm product, dates and the regulatory clock. Anything uncertain goes to people.', tone: 'default' },
    { index: '04 · EXPERTS', title: 'Decide', body: 'Qualified reviewers accept, correct or escalate, with the evidence side by side.', tone: 'amber' },
    { index: '05 · SYSTEM', title: 'Deliver', body: 'E2B(R3) files, screening logs and reports, each with a complete audit trail.', tone: 'default' },
  ],
  assurances: [
    { icon: 'chart', text: 'Evaluation gate on every model, prompt or rule change' },
    { icon: 'list', text: 'Complete, time-stamped, attributable audit trail' },
    { icon: 'lock', text: 'Isolated, encrypted data for every customer' },
    { icon: 'pin', text: 'Hosted in India, with zero-retention model providers' },
  ],
} as const;

export const auditSection = {
  eyebrow: 'VYOM AUDIT',
  heading: 'Check every case. Whoever processed it.',
  lead: 'Most safety teams quality-check a small sample of their vendor’s work, and inspectors look hard at vendor oversight. Vyom Audit checks every processed case and gives your QA team an inspection-ready evidence pack.',
  bullets: [
    'Works across any service provider or safety database',
    'Checks coding against narrative, seriousness logic, missing fields, duplicates and timelines',
    'Findings within 24 hours of case completion (target)',
  ],
  cta: { label: 'Get a free benchmark', href: '/contact' },
} as const;

/** Sample data. Vendor A is fictional and labelled as such. */
export const vendorScorecard = {
  title: 'Vendor scorecard',
  subtitle: 'VENDOR A (FICTIONAL) · Q3 2026',
  stats: [
    { label: 'CASES CHECKED', value: '2,400', tone: 'default' },
    { label: 'COVERAGE', value: '100%', tone: 'accent' },
    { label: 'FINDINGS', value: '194', tone: 'amber' },
  ],
  findingsLabel: 'FINDINGS BY TYPE · SHARE OF CASES',
  findings: [
    { label: 'Coding does not match narrative', value: '74 · 3.1%', width: 100 },
    { label: 'Missing mandatory fields', value: '58 · 2.4%', width: 78 },
    { label: 'Seriousness or outcome inconsistent', value: '29 · 1.2%', width: 39 },
    { label: 'Duplicates not linked', value: '19 · 0.8%', width: 26 },
    { label: 'Late submissions', value: '14 · 0.6%', width: 19 },
  ],
  exportsLabel: 'EXPORTS',
  exports: 'Corrective-action tracker · Inspection evidence pack',
} as const;

export const howWeStart = {
  eyebrow: 'HOW WE START',
  heading: 'Proof before price.',
  lead: 'See Vyom’s quality on your own data before you commit, and keep the evidence either way.',
  stages: [
    {
      number: '01',
      chip: 'WEEKS 1–2 · FREE',
      title: 'Retrospective benchmark',
      body: 'We re-run one quarter of your past literature or cases and show, item by item, what your current process caught and missed. The report is yours to keep.',
      tone: 'accent',
    },
    {
      number: '02',
      chip: 'WEEKS 3–10',
      title: 'Parallel run',
      body: 'Vyom works alongside your current process for eight weeks, measured against recall, accuracy and turnaround targets you agree up front.',
      tone: 'default',
    },
    {
      number: '03',
      chip: 'WEEK 11 ONWARD',
      title: 'Production',
      body: 'Per-case or per-molecule pricing, with quality targets written into the contract and backed by service credits.',
      tone: 'default',
    },
  ],
  /** Explicitly labelled targets, not claims. */
  targetsLabel: 'WHAT EVERY PILOT MUST PROVE · DESIGN TARGETS',
  targets: [
    { value: '≥ 50%', label: 'lower cost per case than your current process' },
    { value: '≥ baseline', label: 'screening recall versus your current process' },
    { value: '100%', label: 'regulatory submissions on time' },
    { value: '< 48 h', label: 'weekly literature turnaround' },
  ],
} as const;

/** Never names a competitor. Categories only. */
export const comparison = {
  eyebrow: 'WHY VYOM',
  heading: 'Built to replace the people-heavy model.',
  lead: 'Services firms grow by adding people. Software platforms leave the work, and the validation, to you. Vyom delivers the outcome and proves it.',
  columns: ['COMPARE', 'SERVICES FIRMS', 'SOFTWARE PLATFORMS', 'VYOM'],
  rows: [
    {
      label: 'What you pay for',
      services: 'Hours and headcount',
      software: 'Licences, plus your own team',
      vyom: 'Outcomes: per case, per molecule',
    },
    {
      label: 'Who does the work',
      services: 'Vendor staff',
      software: 'Your safety team',
      vyom: 'AI agents, signed off by safety physicians',
    },
    {
      label: 'Quality evidence',
      services: 'Small QC samples',
      software: 'Depends on your team',
      vyom: 'Measured on your own data, every week',
    },
    {
      label: 'Independent audit of any vendor',
      services: 'No',
      software: 'No',
      vyom: 'Yes, on 100% of cases',
      quiet: true,
    },
    {
      label: 'Time to go live',
      services: 'Months',
      software: 'Months',
      vyom: 'Weeks (target)',
    },
  ],
} as const;

export const cta = {
  eyebrow: 'BOOK A DEMO',
  heading: 'Connect the evidence. Trace the product. Surface the gaps.',
  lead: 'Walk through Vyom on sample data with the team building it. If it fits, we can scope a free retrospective benchmark on your own records.',
  primary: { label: 'Book a Demo', href: '/book-demo' },
  secondary: { label: 'Explore the Platform', href: '/platform' },
} as const;
