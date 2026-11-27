import { NextResponse, type NextRequest } from 'next/server';
import { siteConfig } from '~/site.config';
import { resolveSession } from '@/lib/auth/resolve';
import {
  SAMPLE_DEFAULT_ROLE,
  SAMPLE_PREFIX,
  SAMPLE_SESSION_SECONDS,
  SAMPLE_TENANT_SLUG,
  SESSION_COOKIE,
  SESSION_COOKIE_OPTIONS,
  homePath,
  isOpsPath,
  isPublicPath,
  tenantSlugFromHost,
  tenantSlugFromPath,
} from '@/lib/auth/session';

/**
 * Edge gateway.
 *
 * Marketing routes pass straight through. /ops and /{tenant} need a session:
 * either a Vyom OS token, verified here (signature, issuer, audience, expiry),
 * or the sample workspace. A tenant route must match the session's tenant,
 * and receives `x-tenant-id`. Pages verify the session again before reading
 * data, so this gateway is a first line, not the only one.
 *
 * A link into the fictional sample tenant (`/demo-pharma/...`) opens it
 * directly when there is no session: the gateway starts a sample session as
 * the PV reviewer for this request and sets the cookie. Sample mode reads only
 * the bundled snapshot and never calls Vyom OS. An expired live session still
 * goes to /login, so nobody is moved from live data to sample data silently.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const ops = isOpsPath(pathname);
  const host = request.headers.get('host') ?? '';
  const tenantSlug = ops
    ? null
    : (tenantSlugFromHost(host, process.env.NEXT_PUBLIC_ROOT_DOMAIN) ?? tenantSlugFromPath(pathname));

  if (!ops && !tenantSlug) {
    return NextResponse.next();
  }

  const cookie = request.cookies.get(SESSION_COOKIE)?.value;
  const session = await resolveSession(cookie);

  const expiredLiveSession = Boolean(cookie) && !cookie?.startsWith(SAMPLE_PREFIX);
  if (!session && tenantSlug === SAMPLE_TENANT_SLUG && siteConfig.sampleWorkspace && !expiredLiveSession) {
    return openSample(request);
  }

  if (!session) {
    const loginUrl = new URL('/login/', request.url);
    loginUrl.searchParams.set('next', pathname);
    const response = NextResponse.redirect(loginUrl);
    if (cookie) response.cookies.delete(SESSION_COOKIE);
    return response;
  }

  const home = new URL(homePath(session.role, session.tenantSlug), request.url);

  if (ops) {
    return session.role === 'ops' ? NextResponse.next() : NextResponse.redirect(home);
  }

  if (session.role === 'ops' || tenantSlug !== session.tenantSlug) {
    return NextResponse.redirect(home);
  }

  const tenantId = session.mode === 'live' ? session.claims.tenantId : session.tenantSlug;
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-tenant-id', tenantId);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

/** Serves this request in the sample workspace and keeps it for the next ones. */
function openSample(request: NextRequest) {
  const value = `${SAMPLE_PREFIX}${SAMPLE_DEFAULT_ROLE}`;
  request.cookies.set(SESSION_COOKIE, value);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-tenant-id', SAMPLE_TENANT_SLUG);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.cookies.set(SESSION_COOKIE, value, { ...SESSION_COOKIE_OPTIONS, maxAge: SAMPLE_SESSION_SECONDS });
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)'],
};
