/** Shared chrome for the product template. Per-product copy lives in products.ts. */

export const productPage = {
  pricingLabel: 'PRICING',
  cta: {
    href: '/contact',
    label: 'Get a free benchmark',
    /** Roadmap modules cannot be benchmarked yet, so they ask differently. */
    roadmapLabel: 'Talk to us about this',
  },

  problemEyebrow: 'THE PROBLEM',

  capabilitiesEyebrow: 'CAPABILITIES',
  capabilitiesHeading: 'What it does.',

  stepsEyebrow: 'HOW IT WORKS',
  stepsHeading: 'Five steps, every time.',

  sampleEyebrow: 'SAMPLE SCREEN',
  sampleHeading: 'What you would be looking at.',
  sampleLead:
    'A concept screen built with sample data and fictional drug codes, to show the shape of the work rather than any real customer’s.',

  targetsEyebrow: 'TARGETS',
  targetsHeading: 'What a pilot has to prove.',
  targetsLead:
    'These are goals we commit to measuring on your own data, not results we are claiming.',

  audienceEyebrow: 'WHO IT IS FOR',
  audienceHeading: 'Built for these teams.',
} as const;

/** The /products index page. */
export const productsIndex = {
  eyebrow: 'MODULES',
  heading: 'One safety system. Three modules.',
  lead: 'Radar takes in and screens, Verify processes and approves cases, Dossier writes the periodic reports. Start with one and add the rest as trust grows; all three share the same rules and evidence trail.',

  matrixEyebrow: 'CAPABILITY MATRIX',
  matrixHeading: 'What each module covers.',
  matrixLead:
    'A tick marks a capability the module states today. Nothing is inferred, so an empty cell means we are not claiming it yet.',
  matrixColumnLabel: 'CAPABILITY',
  plannedLabel: 'Planned',
} as const;
