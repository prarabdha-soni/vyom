/** Navigation, footer and the sitewide notice. Copy only — no markup. */

export type NavLink = {
  readonly label: string;
  readonly href: string;
};

export const notice = {
  label: 'CONCEPT PREVIEW',
  text: 'Product screens show sample data, except Safety Intelligence, which shows public-source records. Figures marked as targets are goals we will prove in pilots.',
} as const;

/** Links beside the Platform menu, which lists the modules itself. */
export const primaryNav: readonly NavLink[] = [
  { label: 'Safety Intelligence', href: '/intelligence' },
  { label: 'VyomBench', href: '/benchmark' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'How we start', href: '/how-we-start' },
  { label: 'Company', href: '/company' },
];

/** The Platform mega-menu: the three modules plus these links underneath. */
export const platformMenu = {
  label: 'Platform',
  heading: 'PLATFORM',
  footer: [
    { label: 'How the platform works', href: '/platform' },
    { label: 'Compare the modules', href: '/products' },
    { label: 'Open the sample workspace', href: '/login' },
  ],
} as const satisfies { label: string; heading: string; footer: readonly NavLink[] };

export const headerActions = {
  secondary: { label: 'Sign in', href: '/login' },
  primary: { label: 'Book a demo', href: '/book-demo' },
} as const;

export const footer = {
  tagline: 'AI-native drug safety, built in India for the world.',
  columns: [
    {
      title: 'MODULES',
      links: [
        { label: 'Vyom Radar', href: '/products/radar' },
        { label: 'Vyom Verify', href: '/products/verify' },
        { label: 'Vyom Dossier', href: '/products/dossier' },
        { label: 'Compare the modules', href: '/products' },
        { label: 'Sample workspace', href: '/login' },
      ],
    },
    {
      title: 'PLATFORM',
      links: [
        { label: 'How it works', href: '/platform' },
        { label: 'Safety Intelligence', href: '/intelligence' },
        { label: 'Official alerts', href: '/intelligence/alerts' },
        { label: 'Evaluation', href: '/platform#evaluation' },
        { label: 'Security and data', href: '/platform#security' },
        { label: 'How we start', href: '/how-we-start' },
      ],
    },
    {
      title: 'COMPANY',
      links: [
        { label: 'About Vyom', href: '/company' },
        { label: 'Careers', href: '/company#careers' },
        { label: 'Pricing', href: '/pricing' },
        { label: 'Book a demo', href: '/book-demo' },
        { label: 'Contact', href: '/contact' },
        { label: 'Sign in', href: '/login' },
      ],
    },
  ],
  legal: [
    { label: 'Privacy', href: '/privacy' },
    { label: 'Terms', href: '/terms' },
  ],
  copyright:
    '© 2026 Vyom. Concept preview: product screens show sample data; Safety Intelligence shows public-source records.',
  meaning: 'Vyom (व्योम) is Sanskrit for sky.',
} as const satisfies {
  tagline: string;
  columns: readonly { title: string; links: readonly NavLink[] }[];
  legal: readonly NavLink[];
  copyright: string;
  meaning: string;
};
