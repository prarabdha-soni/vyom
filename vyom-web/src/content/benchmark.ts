export type BenchmarkRun = {
  readonly model: string;
  readonly task: string;
  readonly date: string;
  readonly resultHref?: string;
};

export const benchmarkRuns: readonly BenchmarkRun[] = [];

export const benchmarkPage = {
  title: 'VyomBench results',
  description:
    'Public-data benchmark results for pharmacovigilance literature extraction, when runs are available.',
  eyebrow: 'VYOMBENCH · RESULTS',
  heading: 'Benchmark results, with the method attached.',
  lead:
    'Only completed, reviewable runs are listed here. No model scores are published until a result is available.',
  task: {
    label: 'Task',
    value: 'Extract patient sex, age group, suspect drugs, reactions and seriousness from a BioDEX abstract.',
    source: 'BioDEX-ICSR abstracts, evaluated against linked FAERS reports.',
  },
  methodLink: { label: 'Read the method', href: '#method' },
  runsHeading: 'Published runs',
  emptyState: 'No benchmark runs are published yet.',
  unpublishedRun: {
    model: 'Not published',
    task: 'Extract patient sex, age group, suspect drugs, reactions and seriousness from a BioDEX abstract.',
    date: 'Not published',
  },
  resultLinkLabel: 'View result',
  runLabels: { model: 'Model', task: 'Task', date: 'Date' },
  method: {
    id: 'method',
    eyebrow: 'METHOD',
    heading: 'Public data. Field-level scoring.',
    closingCitationLabel: 'Method and source notes',
    body:
      'Each run records its model identifier, task, run date, token usage, latency and estimated provider cost. Scalar fields use normalized exact matching; drug and reaction lists use normalized set overlap. Precision, recall and F1 are reported by field.',
    limitation:
      'BioDEX dataset cards currently declare no dataset licence. Source abstracts, linked reports and row-level results are not reproduced on this page. Reaction matching does not redistribute or depend on a MedDRA hierarchy.',
    sources: [
      {
        label: 'BioDEX-ICSR dataset card',
        href: 'https://huggingface.co/datasets/BioDEX/BioDEX-ICSR',
      },
      {
        label: 'openFDA drug event API',
        href: 'https://open.fda.gov/apis/drug/event/',
      },
    ],
  },
} as const;