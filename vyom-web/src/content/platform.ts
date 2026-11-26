/** /platform — how the system works, what we measure, and how data is held. */

export const platformPage = {
  eyebrow: 'PLATFORM',
  heading: 'AI proposes. Rules check. Experts decide.',
  lead: 'Every step leaves evidence. No case is excluded by AI alone until its measured accuracy on your data meets a threshold your qualified person has approved.',

  principle: {
    eyebrow: 'THE PRINCIPLE',
    heading: 'Nothing is dropped on a model’s say-so.',
    body: 'An agent can propose that an item is not a valid case. It cannot act on that alone. Until the measured accuracy for that decision, on your data, clears a threshold your qualified person has signed off, every exclusion goes to a person. The threshold is yours to set, and it is written down.',
    points: [
      {
        title: 'Measured first',
        body: 'Accuracy is measured on your own historical data before anything runs unattended.',
      },
      {
        title: 'Approved by your QP',
        body: 'Your qualified person approves the threshold for each decision type, in writing.',
      },
      {
        title: 'Reversible',
        body: 'If measured accuracy drops below the threshold, the decision returns to people automatically.',
      },
    ],
  },

  architecture: {
    eyebrow: 'ARCHITECTURE',
    heading: 'Five stages, one evidence trail.',
    lead: 'The same pipeline runs behind every product. Blue is an agent proposing; amber is a person deciding.',
  },

  measurement: {
    eyebrow: 'WHAT WE MEASURE',
    heading: 'The numbers we report back.',
    lead: 'These are the measures themselves, not results. Each one is measured on your own data in every pilot and reported to you, whatever it says.',
    /** The label every metric card carries. */
    badge: 'MEASURED IN EVERY PILOT',
    metrics: [
      {
        name: 'Recall',
        body: 'Of the valid cases present in a period, the share the system found.',
      },
      {
        name: 'False negatives per 1,000 items',
        body: 'How many valid cases were missed, at a rate you can compare across periods.',
      },
      {
        name: 'Precision',
        body: 'Of the items flagged for review, the share that turned out to be valid.',
      },
      {
        name: 'Extraction completeness',
        body: 'The share of mandatory fields filled correctly from the source, without a person retyping them.',
      },
      {
        name: 'Reviewer minutes per item',
        body: 'How long a qualified reviewer actually spends on an item, start to decision.',
      },
      {
        name: 'On-time rate',
        body: 'The share of regulatory submissions made inside the reporting clock.',
      },
    ],
  },

  evaluation: {
    eyebrow: 'EVALUATION',
    heading: 'Every change passes a gate.',
    body: 'Model, prompt and rule changes run against gold sets before they reach your data. A change that moves recall the wrong way does not ship.',
  },

  auditTrail: {
    eyebrow: 'AUDIT TRAIL',
    heading: 'Every decision, reconstructable.',
    lead: 'Each decision records what proposed it, which versions were running, the exact words it came from, who decided, and when. An inspector can replay any case.',
    recordLabel: 'AUDIT RECORD',
    /** Sample data: fictional case, fictional reviewer. */
    record: [
      { key: 'case_id', value: 'VY-CASE-0412' },
      { key: 'decision', value: 'seriousness = serious (hospitalisation)' },
      { key: 'proposed_by', value: 'agent:seriousness' },
      { key: 'model_version', value: 'vyom-sx-2026.08.3' },
      { key: 'prompt_version', value: 'seriousness/v14' },
      { key: 'rule_version', value: 'gvp-vi/2026.07' },
      { key: 'evidence_span', value: 'source:lit-1184 · chars 412–457' },
      { key: 'evidence_text', value: '"was hospitalised two weeks after starting VY-201"' },
      { key: 'confidence', value: '0.97' },
      { key: 'reviewer', value: 'qp:a.sharma (fictional)' },
      { key: 'reviewer_action', value: 'approved' },
      { key: 'timestamp', value: '2026-10-12T09:04:38+05:30' },
    ],
  },

  security: {
    eyebrow: 'SECURITY AND DATA',
    heading: 'Where your data lives, and what touches it.',
    items: [
      {
        icon: 'pin',
        title: 'Hosted in India',
        body: 'Your data is processed and stored in Indian regions, under the DPDP Act.',
      },
      {
        icon: 'lock',
        title: 'Encrypted in transit and at rest',
        body: 'Standard transport encryption, and encryption at rest for every store.',
      },
      {
        icon: 'shield',
        title: 'Isolated per customer',
        body: 'Each customer’s data sits in its own isolated tenant. Nothing is pooled.',
      },
      {
        icon: 'ban',
        title: 'No training on your data',
        body: 'We do not train models on your data. If we ever propose to, it needs your written consent first, per product.',
      },
      {
        icon: 'clock',
        title: 'Zero-retention model providers',
        body: 'Model providers are used under zero-retention terms, so prompts and outputs are not kept or trained on by them.',
      },
      {
        icon: 'list',
        title: 'Access is logged',
        body: 'Who looked at what, and when, is recorded with the same audit trail as every other action.',
      },
    ],
  },
} as const;

/** The engine architecture drawn on /platform. */
export const architecture = {
  flow: [
    { title: 'Ingest', tone: 'default' },
    { title: 'Understand', tone: 'accent' },
    { title: 'Check', tone: 'default' },
    { title: 'Decide', tone: 'amber' },
    { title: 'Deliver', tone: 'default' },
  ],
  foundationLabel: 'ON A FOUNDATION OF',
  foundation: [
    { title: 'Evaluation', body: 'Gold sets gate every change' },
    { title: 'Audit trail', body: 'Time-stamped and attributable' },
    { title: 'Model gateway', body: 'One controlled interface' },
    { title: 'Tenant isolation', body: 'Separate, encrypted per customer' },
  ],
} as const;
