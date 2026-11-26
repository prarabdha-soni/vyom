/**
 * The three Vyom modules. Shared by the mega-menu, the home page, the module
 * pages and the signed-in console, so a name changes in one place.
 *
 *   Radar   — intake and literature screening
 *   Verify  — case processing, medical review and quality checks
 *   Dossier — periodic reports from data lock to sign-off
 */

export type ProductSlug = 'radar' | 'verify' | 'dossier';

export type ProductStatus = 'design-partners' | 'roadmap';

export type Product = {
  readonly slug: ProductSlug;
  readonly name: string;
  /** The short name used inside the console, e.g. "Radar". */
  readonly shortName: string;
  /** Mono label above the name in the mega-menu. */
  readonly kicker: string;
  /** One line, used in the mega-menu: where you start and where you end up. */
  readonly summary: string;
  /** The headline on cards and the module page. */
  readonly headline: string;
  /** The card body. */
  readonly description: string;
  /** Pricing shape, shown as a chip. Never a number. */
  readonly pricing: string;
  /** Pricing unit, shown in the module page hero. Never a number. */
  readonly pricingUnit: string;
  readonly status: ProductStatus;
  /** What this module exists to fix. One paragraph. */
  readonly problem: string;
  /** What it does. Rendered as a ticked list. */
  readonly capabilities: readonly string[];
  /** Numbered steps, derived from the capabilities above. */
  readonly steps: readonly { readonly title: string; readonly body: string }[];
  /**
   * What each pilot must prove. Every entry is a goal, never a result, and is
   * rendered behind a "Target" label.
   */
  readonly targets: readonly string[];
  /** Who the module is for. */
  readonly audience: readonly string[];
  /** Caption shown above the sample screen. */
  readonly sampleScreenLabel: string;
};

/** Which module is given the large card. */
export const flagship: ProductSlug = 'verify';

export const statusLabel: Record<ProductStatus, string> = {
  'design-partners': 'DESIGN PARTNERS NOW',
  roadmap: 'ROADMAP',
};

export const products: readonly Product[] = [
  {
    slug: 'radar',
    name: 'Vyom Radar',
    shortName: 'Radar',
    kicker: '01 · INTAKE',
    summary: 'From scattered inboxes and journals to one screened, structured intake.',
    headline: 'Every inbox and every journal, screened and structured.',
    description:
      'Weekly literature screening and case intake from safety email, call notes and forms, de-duplicated and triaged, with every decision left to your team.',
    pricing: 'PER MOLECULE / MONTH',
    pricingUnit: 'Per molecule per month',
    problem:
      'Safety information arrives in journals, inboxes, call notes and forms. Screening it every week for every molecule is slow, and hard to prove complete.',
    capabilities: [
      'Approved search strategies for global and Indian journals',
      'Weekly retrieval and de-duplication',
      'Screening for valid cases and special situations: pregnancy, overdose and misuse',
      'Intake from safety email, call transcripts and forms',
      'Day zero recorded the moment a person confirms a valid case',
      'Weekly screening log',
      'Measured recall reports',
    ],
    steps: [
      {
        title: 'Agree the strategy',
        body: 'Search strategies are written and approved with your team before anything runs.',
      },
      {
        title: 'Retrieve and de-duplicate',
        body: 'Journals, inboxes and call notes are collected every week and de-duplicated against what you have already seen.',
      },
      {
        title: 'Screen',
        body: 'Each item is triaged for patient, reporter, suspect drug, event and seriousness, and placed in a review, escalate or close band.',
      },
      {
        title: 'Decide',
        body: 'A reviewer confirms each item: valid case, safety information, not relevant or escalate. Nothing closes on its own.',
      },
      {
        title: 'Open the case and log',
        body: 'A confirmed case opens in Vyom Verify with its clock started, and the week closes with a screening log.',
      },
    ],
    targets: [
      'Recall at or above your current process',
      'Turnaround under 48 hours',
      'Full audit trail',
    ],
    audience: [
      'Generics exporters with large portfolios',
      'Companies that outsource literature screening today',
    ],
    sampleScreenLabel: 'ONE WEEK OF SCREENING',
    status: 'design-partners',
  },
  {
    slug: 'verify',
    name: 'Vyom Verify',
    shortName: 'Verify',
    kicker: '02 · CASES',
    summary: 'From manual case work to evidence-backed, physician-approved cases.',
    headline: 'Every case evidence-backed, every decision physician-approved.',
    description:
      'Validity, coding, seriousness, expectedness, narrative and E2B(R3) output, with every field linked to its source and every case approved by a safety physician.',
    pricing: 'PRICED PER CASE',
    pricingUnit: 'Per case',
    problem:
      'Case processing is the largest line in most safety budgets, it is still mostly manual, and most teams can check only a small sample of the work.',
    capabilities: [
      'Validity check: patient, reporter, suspect drug and event',
      'Seriousness and expectedness against your reference safety information',
      'MedDRA and WHODrug coding suggestions, under your own licences',
      'Narrative drafts with every sentence linked to its source',
      'Duplicate detection and regulatory clock tracking',
      'Causality and approval by a safety physician',
      'E2B(R3) output',
      'Independent checks on cases processed by any vendor, with scorecards',
    ],
    steps: [
      {
        title: 'Structure',
        body: 'Patient, reporter, products and events are extracted, and every field keeps the passage it came from.',
      },
      {
        title: 'Check',
        body: 'Validity, seriousness, expectedness and the regulatory clock are worked out by fixed rules, not by a model.',
      },
      {
        title: 'Draft',
        body: 'A narrative is drafted citing the source, and coding suggestions are offered for review.',
      },
      {
        title: 'Decide',
        body: 'A safety physician records causality and approves, returns or escalates, with the evidence beside them.',
      },
      {
        title: 'Deliver and prove',
        body: 'Approved cases produce E2B(R3) output, and every change is kept in a version history an inspector can read.',
      },
    ],
    targets: [
      'At least 50% lower cost per case',
      '100% on-time submissions',
      'Quality at or above your current process',
    ],
    audience: [
      'Drug-safety teams at generics exporters and mid-sized pharma',
      'Heads of quality who oversee outsourced case processing',
    ],
    sampleScreenLabel: 'CASE QUEUE, CASE DETAIL AND QUALITY CHECKS',
    status: 'design-partners',
  },
  {
    slug: 'dossier',
    name: 'Vyom Dossier',
    shortName: 'Dossier',
    kicker: '03 · REPORTS',
    summary: 'From data lock to QPPV sign-off, every statement traceable to its source.',
    headline: 'Periodic reports, traceable from data lock to sign-off.',
    description:
      'PBRER and PADER sections drafted from a sealed data package, with line listings, summary tabulations and literature summaries, reviewed section by section and signed off by your QPPV.',
    pricing: 'PER REPORT',
    pricingUnit: 'Per report',
    problem:
      'PBRERs, PSURs and US periodic reports take weeks of assembly before experts can start writing, and it is hard to show where each statement came from.',
    capabilities: [
      'Data lock with a sealed evidence package',
      'Line listings and summary tabulations',
      'Section drafts citing the data behind every statement',
      'Author, reviewer and approver steps for each section',
      'Literature summaries for the reporting interval',
      'QPPV sign-off with re-authentication',
      'Version history and provenance trail',
    ],
    steps: [
      {
        title: 'Lock the data',
        body: 'Cases and literature for the interval are frozen at the data lock point into a sealed evidence package.',
      },
      {
        title: 'Tabulate',
        body: 'Line listings and summary tabulations are generated from the package, not typed.',
      },
      {
        title: 'Draft',
        body: 'Sections are drafted from aggregates only, and any number or reference not in the package is flagged.',
      },
      {
        title: 'Review',
        body: 'Authors, reviewers and approvers work section by section, with the provenance of every statement one click away.',
      },
      {
        title: 'Sign off',
        body: 'The QPPV signs off after re-entering their password, and the signed version is kept unchanged.',
      },
    ],
    targets: ['Report assembly time cut from weeks to days'],
    audience: ['Safety writers and qualified persons for pharmacovigilance'],
    sampleScreenLabel: 'REPORT WORKSPACE',
    status: 'design-partners',
  },
];

export function getProduct(slug: ProductSlug): Product {
  const product = products.find((candidate) => candidate.slug === slug);
  if (!product) throw new Error(`Unknown product: ${slug}`);
  return product;
}

export const flagshipProduct = getProduct(flagship);

/* ---------------------------------------------------------------------------
   Capability matrix for /products.

   A tick appears only where that module's own capability list above states it.
   Nothing is inferred, so an empty cell means "not claimed", not "impossible".
   --------------------------------------------------------------------------- */

export type MatrixRow = {
  readonly capability: string;
  readonly products: readonly ProductSlug[];
  /** Rendered as a dashed tick: stated as planned rather than available. */
  readonly planned?: readonly ProductSlug[];
};

export const capabilityMatrix: readonly MatrixRow[] = [
  { capability: 'Weekly literature screening', products: ['radar'] },
  { capability: 'Intake from email, call notes and forms', products: ['radar'] },
  { capability: 'De-duplication', products: ['radar', 'verify'] },
  { capability: 'Seriousness and expectedness rules', products: ['verify'] },
  { capability: 'MedDRA and WHODrug coding suggestions', products: ['verify'] },
  { capability: 'Drafts that cite their source', products: ['verify', 'dossier'] },
  { capability: 'Regulatory clock', products: ['radar', 'verify'] },
  { capability: 'E2B(R3) output', products: ['verify'] },
  { capability: 'Checks cases from any vendor', products: ['verify'] },
  { capability: 'Sealed data package at data lock', products: ['dossier'] },
  { capability: 'Expert decision before anything is final', products: ['radar', 'verify', 'dossier'] },
  { capability: 'Audit trail and version history', products: ['radar', 'verify', 'dossier'] },
];

export const matrixNote =
  'A tick marks a capability the module states today. Signal management is on the roadmap.';

/* ---------------------------------------------------------------------------
   Sample data for the product-page screens. Fictional codes only, and every
   screen that shows these carries a SAMPLE DATA chip.
   --------------------------------------------------------------------------- */

/** Vyom Verify — the detail pane beside the queue. */
export const caseDetail = {
  caseId: 'VY-CASE-0412',
  status: 'AWAITING PHYSICIAN',
  fields: [
    { label: 'PATIENT', value: '54-year-old woman', confidence: '0.98' },
    { label: 'SUSPECT DRUG', value: 'VY-201', confidence: '0.99' },
    { label: 'EVENT', value: 'Elevated liver enzymes', confidence: '0.96' },
    { label: 'MEDDRA PT', value: 'Hepatotoxicity', confidence: '0.94' },
    { label: 'SERIOUSNESS', value: 'Hospitalisation', confidence: '0.97' },
    { label: 'EXPECTEDNESS', value: 'Unlisted for VY-201', confidence: '0.91' },
  ],
  passageLabel: 'SOURCE PASSAGE · JOURNAL ARTICLE',
  passage: [
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
  actions: ['Approve', 'Correct', 'Escalate'],
  note: 'AI PROPOSES · PHYSICIAN DECIDES',
} as const;

/** Vyom Radar — the five-stage funnel. */
export const literatureStages = {
  label: 'ONE WEEK',
  rows: [
    { label: 'Articles retrieved', value: '4,820', width: 100, tone: 'muted' },
    { label: 'Unique after de-duplication', value: '3,910', width: 81, tone: 'muted' },
    { label: 'Flagged by AI for review', value: '212', width: 4.4, tone: 'accent' },
    { label: 'Valid cases confirmed', value: '41', width: 0.9, tone: 'amber' },
    { label: 'Case-ready drafts written', value: '41', width: 0.9, tone: 'amber' },
  ],
} as const;

export const flaggedArticles = {
  label: 'FLAGGED ARTICLES',
  columns: ['REFERENCE', 'MOLECULE', 'REASON'],
  rows: [
    { ref: 'VY-LIT-1184', molecule: 'VY-201', reason: 'Valid case', tone: 'accent' },
    { ref: 'VY-LIT-1190', molecule: 'VY-305', reason: 'Pregnancy', tone: 'amber' },
    { ref: 'VY-LIT-1203', molecule: 'VY-201', reason: 'Overdose', tone: 'amber' },
    { ref: 'VY-LIT-1217', molecule: 'VY-412', reason: 'Valid case', tone: 'accent' },
    { ref: 'VY-LIT-1224', molecule: 'VY-305', reason: 'Not relevant – QC sample', tone: 'default' },
  ],
} as const;

/** Vyom Verify — quality checks: a six-month finding-rate trend beside the scorecard. */
export const auditTrend = {
  label: 'FINDINGS PER 100 CASES · VENDOR A (FICTIONAL)',
  points: [
    { month: 'APR', value: 11.4 },
    { month: 'MAY', value: 10.1 },
    { month: 'JUN', value: 9.6 },
    { month: 'JUL', value: 9.8 },
    { month: 'AUG', value: 8.7 },
    { month: 'SEP', value: 8.1 },
  ],
} as const;

/** Vyom Dossier — a periodic report outline with per-section status. */
export const reportOutline = {
  title: 'PBRER · VY-201 · Jan–Jun 2026',
  sections: [
    { number: '1', title: 'Introduction', status: 'Auto-filled', tone: 'accent' },
    { number: '2', title: 'Worldwide marketing authorisation status', status: 'Auto-filled', tone: 'accent' },
    { number: '3', title: 'Actions taken for safety reasons', status: 'Needs input', tone: 'amber' },
    { number: '4', title: 'Changes to reference safety information', status: 'Draft ready', tone: 'accent' },
    { number: '5', title: 'Estimated exposure', status: 'Needs input', tone: 'amber' },
    { number: '6', title: 'Data in summary tabulations', status: 'Draft ready', tone: 'accent' },
    { number: '7', title: 'Summaries of significant findings from literature', status: 'In review', tone: 'amber' },
    { number: '8', title: 'Signal evaluation', status: 'In review', tone: 'amber' },
    { number: '9', title: 'Benefit-risk evaluation', status: 'Physician authoring', tone: 'amber' },
  ],
} as const;

/* ---------------------------------------------------------------------------
   Navigation between product pages
   --------------------------------------------------------------------------- */

export type ProductNeighbours = {
  readonly previous: Product | null;
  readonly next: Product | null;
};

/** The previous and next product in `products` order. The list does not wrap. */
export function getProductNeighbours(slug: ProductSlug): ProductNeighbours {
  const index = products.findIndex((product) => product.slug === slug);
  return {
    previous: index > 0 ? (products[index - 1] ?? null) : null,
    next: index < products.length - 1 ? (products[index + 1] ?? null) : null,
  };
}
