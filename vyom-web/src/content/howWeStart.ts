/** /how-we-start — the three stages in depth, plus the questions we are always asked. */

export const howWeStartPage = {
  eyebrow: 'HOW WE START',
  heading: 'Proof before price.',
  lead: 'See Vyom’s quality on your own data before you commit, and keep the evidence either way.',

  stagesHeading: 'Three stages, about eleven weeks.',

  stages: [
    {
      number: '01',
      chip: 'WEEKS 1–2 · FREE',
      title: 'Retrospective benchmark',
      summary:
        'We re-run one quarter of your past literature or cases and show, item by item, what your current process caught and missed.',
      tone: 'accent',
      whatWeNeed: 'One quarter of past cases or literature search results, and the search strategies you used.',
      whatYouGet: [
        'An item-by-item comparison against your own completed work',
        'Recall, precision and extraction completeness measured on your data',
        'A written report you keep, whether or not you go further',
      ],
      commitment: 'No cost, no integration, no commitment.',
    },
    {
      number: '02',
      chip: 'WEEKS 3–10',
      title: 'Parallel run',
      summary:
        'Vyom works alongside your current process for eight weeks, measured against targets you agree up front.',
      tone: 'default',
      whatWeNeed: 'A live feed of the same work your current process receives, and a named reviewer on your side.',
      whatYouGet: [
        'Weekly measurement against the recall, accuracy and turnaround targets you set',
        'Your reviewers working in the console, so the handover is already done',
        'A threshold proposal for your qualified person to approve or reject',
      ],
      commitment: 'Your existing process stays in charge throughout. Nothing we produce is submitted without your sign-off.',
    },
    {
      number: '03',
      chip: 'WEEK 11 ONWARD',
      title: 'Production',
      summary:
        'Per-case or per-molecule pricing, with quality targets written into the contract and backed by service credits.',
      tone: 'default',
      whatWeNeed: 'A signed agreement, and the thresholds your qualified person approved in stage two.',
      whatYouGet: [
        'Pricing per case or per molecule, not per head',
        'The targets from your pilot written into the contract',
        'Service credits if we miss them, and monthly measurement either way',
      ],
      commitment: 'If the pilot does not clear the targets, there is nothing to sign.',
    },
  ],

  needLabel: 'WHAT WE NEED',
  getLabel: 'WHAT YOU GET',
  commitmentLabel: 'COMMITMENT',

  faq: {
    eyebrow: 'QUESTIONS',
    heading: 'What people ask first.',
    items: [
      {
        question: 'What data do you need to start?',
        answer:
          'For a literature benchmark: your search strategies and one quarter of past search results, with the screening decisions you made. For a case benchmark: one quarter of completed cases, in E2B(R3) or whatever export your safety database produces. Nothing live, and no integration — a secure file transfer is enough to begin.',
      },
      {
        question: 'How does pricing work?',
        answer:
          'Per unit of work, not per person: per case processed, per case checked, per molecule per month for literature, or per report. The retrospective benchmark is free. We quote production pricing only after a parallel run, because until then neither of us knows the real volume and mix. Pricing is not published, because it depends on your portfolio — ask and we will send a quote.',
      },
      {
        question: 'How does validation work?',
        answer:
          'Accuracy is measured on your own data, not on a public benchmark. Every model, prompt and rule change runs against gold sets before it reaches you. No decision type runs unattended until its measured accuracy clears a threshold your qualified person has approved in writing, and if accuracy drops below that threshold the decision returns to people automatically. Every decision is recorded with the versions that produced it, so any case can be replayed.',
      },
      {
        question: 'What happens to our data?',
        answer:
          'It is processed and stored in India, encrypted in transit and at rest, and isolated in your own tenant. We do not train models on it, and model providers are used under zero-retention terms. You can ask for your data to be deleted at any point, including after a benchmark. Access is logged in the same audit trail as everything else.',
      },
      {
        question: 'What if the benchmark makes us look bad?',
        answer:
          'The report is yours either way, and it is yours alone — we do not use your results as a reference or a case study without a separate written agreement. If the benchmark shows your current process is already ahead, we will tell you that.',
      },
      {
        question: 'Do we have to replace our safety database?',
        answer:
          'No. The quality checks in Vyom Verify work against whatever system you already run. For case processing we produce E2B(R3) output, and connection to existing safety databases is on the roadmap.',
      },
    ],
  },
} as const;
