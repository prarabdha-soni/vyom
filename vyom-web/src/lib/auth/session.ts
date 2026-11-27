/**
 * Session cookie and path helpers shared by the edge gateway, the server
 * actions and the console. Edge-safe: no Node APIs, no server-only imports.
 */

import { isRole, type Role } from './roles';

/**
 * One httpOnly cookie holds the session. Its value is either the Vyom OS
 * session token (a signed JWT) or `sample:<role>` for the sample workspace,
 * which never talks to a backend.
 */
export const SESSION_COOKIE = 'vyom_session';
export const SAMPLE_PREFIX = 'sample:';

/** The fictional tenant the sample workspace shows. */
export const SAMPLE_TENANT_SLUG = 'demo-pharma';

/** Eight hours, matching the Vyom OS default session lifetime. */
export const SAMPLE_SESSION_SECONDS = 8 * 60 * 60;

/** First URL segments that are never a tenant slug. */
export const RESERVED_PATHS = [
  'products',
  'platform',
  'how-we-start',
  'company',
  'contact',
  'privacy',
  'terms',
  'pricing',
  'book-demo',
  'quality',
  'benchmark',
  'intelligence',
  'login',
  'ops',
  'api',
  'healthz',
] as const;

const PUBLIC_EXACT = new Set([
  '',
  '/',
  '/login',
  '/pricing',
  '/book-demo',
  '/intelligence',
  '/products',
  '/platform',
  '/how-we-start',
  '/company',
  '/contact',
  '/privacy',
  '/terms',
  '/quality',
  '/benchmark',
  // Load-balancer health check (container deployments).
  '/healthz',
  // Crawler files: the edge gateway must never send these to /login.
  '/robots.txt',
  '/sitemap.xml',
]);

const PUBLIC_PREFIXES = [
  '/products/',
  '/platform/',
  '/how-we-start/',
  '/company/',
  '/contact/',
  '/privacy/',
  '/terms/',
  '/pricing/',
  '/book-demo/',
  '/intelligence/',
  '/login/',
] as const;

export function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

export function isPublicPath(pathname: string): boolean {
  const path = normalizePath(pathname);
  if (PUBLIC_EXACT.has(path)) return true;
  return PUBLIC_PREFIXES.some((prefix) => path.startsWith(prefix));
}

export function isOpsPath(pathname: string): boolean {
  const path = normalizePath(pathname);
  return path === '/ops' || path.startsWith('/ops/');
}

export function tenantSlugFromPath(pathname: string): string | null {
  const path = normalizePath(pathname);
  const segment = path.split('/').filter(Boolean)[0];
  if (!segment) return null;
  if ((RESERVED_PATHS as readonly string[]).includes(segment)) return null;
  return segment;
}

export function tenantSlugFromHost(host: string, rootDomain: string | undefined): string | null {
  if (!rootDomain) return null;
  const hostname = host.split(':')[0] ?? '';
  const suffix = `.${rootDomain}`;
  if (!hostname.endsWith(suffix)) return null;
  const sub = hostname.slice(0, -suffix.length);
  if (!sub || sub === 'www' || sub === 'app') return null;
  if ((RESERVED_PATHS as readonly string[]).includes(sub)) return null;
  return sub;
}

/** Only same-origin absolute paths; never `//host` or a full URL. */
export function safeNextPath(candidate: string | null | undefined): string | null {
  if (!candidate) return null;
  if (!candidate.startsWith('/') || candidate.startsWith('//') || candidate.startsWith('/\\')) return null;
  return candidate;
}

/** The role inside a `sample:<role>` cookie, or null when the value is anything else. */
export function sampleRole(value: string | undefined): Role | null {
  if (!value?.startsWith(SAMPLE_PREFIX)) return null;
  const role = value.slice(SAMPLE_PREFIX.length);
  return isRole(role) ? role : null;
}

/** Where a signed-in user lands. */
export function homePath(role: Role, tenantSlug: string): string {
  return role === 'ops' ? '/ops/' : `/${tenantSlug}/dashboard/`;
}
