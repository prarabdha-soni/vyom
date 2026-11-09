const scheduleMUrl =
  'https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadGazette_NotificationsFiles/2023.12.28_DR_Final%20G.S.R.%20922(E).pdf';

export const qualityMeta = {
  title: 'Schedule M readiness',
  description:
    'A source-linked overview of Schedule M topics for organizing a pharmaceutical quality readiness review.',
} as const;

export const qualityPage = {
  eyebrow: 'SCHEDULE M · SOURCE-LINKED',
  heading: 'Prepare for a Schedule M readiness review.',
  lead:
    'Use this source-linked overview to organize evidence and questions before a readiness discussion. It is informational only, not a compliance determination, certification or regulatory opinion.',
  notice: {
    heading: 'Primary source',
    body:
      'G.S.R. 922(E), dated 28 December 2023, substitutes Schedule M in the Drugs Rules, 1945. The notification and its Schedule are the source for the topics below.',
    citation: 'G.S.R. 922(E), 28 Dec 2023 · Schedule M',
    href: scheduleMUrl,
  },
  readiness: {
    eyebrow: 'READINESS REVIEW AREAS',
    heading: 'Organize the evidence by requirement.',
    lead:
      'These topics summarize sections of the cited Schedule M. Use the notification itself for the complete text and applicability.',
  },
  areas: [
    {
      title: 'Pharmaceutical quality system and risk',
      body:
        'The Schedule describes a documented pharmaceutical quality system, management responsibilities and quality risk management across relevant activities.',
      citation: 'Part I, sections 1–2',
    },
    {
      title: 'Qualification and validation',
      body:
        'The Schedule covers qualification and validation planning, documented evidence, reports and continued review of validated systems.',
      citation: 'Part I, section 5',
    },
    {
      title: 'People, premises and equipment',
      body:
        'The Schedule addresses personnel, training, premises, storage areas, equipment, maintenance and calibration.',
      citation: 'Part I, sections 11–13',
    },
    {
      title: 'Materials, production and quality control',
      body:
        'The Schedule covers material controls, production records, in-process controls, laboratory controls and batch record review.',
      citation: 'Part I, sections 14, 18–19',
    },
    {
      title: 'Documentation and computerised systems',
      body:
        'The Schedule describes controlled documents and records, including controls for GMP-related computerised systems.',
      citation: 'Part I, sections 17, 20',
    },
    {
      title: 'Review, complaints and self-inspection',
      body:
        'The Schedule includes product quality reviews, complaint handling, product recalls, self-inspection and follow-up actions.',
      citation: 'Part I, sections 2.3, 6–7, 10',
    },
  ].map((area) => ({ ...area, href: scheduleMUrl })),
  closing:
    'Applicability and implementation depend on the licensed activities and the current rules. Confirm requirements against the Gazette notification and the relevant licensing authority.',
  closingCitation: 'G.S.R. 922(E) · Schedule M',
  informationalChip: 'INFORMATIONAL · NOT A CERTIFICATION',
  cta: { label: 'Discuss a readiness review', href: '/contact' },
} as const;