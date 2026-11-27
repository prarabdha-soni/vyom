import { NextResponse, type NextRequest } from 'next/server';
import { resolveSession } from '@/lib/auth/resolve';
import {
  SESSION_COOKIE,
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

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)'],
};
