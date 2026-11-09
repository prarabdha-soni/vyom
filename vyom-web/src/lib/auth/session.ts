/** Cookie and path helpers shared by the edge gateway and the login stub. */

export const AUTH_COOKIE = 'vyom_token';
export const TENANT_COOKIE = 'vyom_tenant';
export const ROLE_COOKIE = 'vyom_role';

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

export function safeNextPath(candidate: string | null): string | null {
  if (!candidate) return null;
  if (!candidate.startsWith('/') || candidate.startsWith('//')) return null;
  return candidate;
}
