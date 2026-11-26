/**
 * Single source of flags and owner-supplied placeholders.
 *
 * Placeholders keep their square brackets until the owner replaces them, so an
 * unreplaced value is obvious on the page rather than silently shipping.
 */

/**
 * Resolves the canonical origin for this build. See `siteConfig.url`.
 */
function resolveSiteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (explicit) return explicit.replace(/\/$/, '');

  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim();
  if (vercel) return `https://${vercel.replace(/\/$/, '')}`;

  return 'http://localhost:3000';
}

export const siteConfig = {
  name: 'Vyom',
  /**
   * Canonical origin, used for canonical URLs, sitemap.xml and the Open Graph
   * image URL. Resolved at build time, in order:
   *
   *   1. NEXT_PUBLIC_SITE_URL          — set this once the real domain is live
   *   2. VERCEL_PROJECT_PRODUCTION_URL — the project's vercel.app domain
   *   3. http://localhost:3000         — local builds
   *
   * Deliberately not hardcoded: a guessed domain silently produces broken
   * canonical, sitemap and share-image URLs.
   */
  url: resolveSiteUrl(),
  locale: 'en-IN',

  /** Shows the "Concept preview" bar sitewide. One flag, as agreed. */
  showNotice: true,

  /**
   * While false, every page emits <meta name="robots" content="noindex"> and
   * robots.txt disallows everything. Flip to true only when the site is ready
   * to be found.
   */
  indexable: true,

  /**
   * Offers the sample workspace on /login: the fictional tenant demo-pharma,
   * browsable without a backend. Its data is SAMPLE DATA and changes made
   * there are not saved.
   */
  sampleWorkspace: true,

  /** Placeholders — replace the bracketed values. */
  email: '[YOUR EMAIL]',
  location: 'Gurugram, India',
  locationMono: 'GURUGRAM, INDIA',
} as const;

export type SiteConfig = typeof siteConfig;

/** True while a placeholder is still unreplaced. */
export function isPlaceholder(value: string): boolean {
  return value.startsWith('[') && value.endsWith(']');
}
