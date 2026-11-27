'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { siteConfig } from '~/site.config';
import { osFetch } from '@/lib/gateway/api-client';
import { resolveSession } from './resolve';
import { isRole } from './roles';
import {
  SAMPLE_PREFIX,
  SAMPLE_SESSION_SECONDS,
  SAMPLE_TENANT_SLUG,
  SESSION_COOKIE,
  homePath,
  safeNextPath,
} from './session';
import { sessionSecret, verifySessionToken } from './token';

export type SignInState = { readonly error: string | null; readonly email?: string };

const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
};

/** Only follow `next` when it stays inside the place this session may go. */
function landing(next: FormDataEntryValue | null, home: string, tenantSlug: string, ops: boolean): string {
  const candidate = safeNextPath(typeof next === 'string' ? next : null);
  if (!candidate) return home;
  const allowed = ops ? candidate.startsWith('/ops') : candidate.startsWith(`/${tenantSlug}/`);
  return allowed ? candidate : home;
}

/** Signs in against Vyom OS and keeps its token in an httpOnly cookie. */
export async function signIn(_previous: SignInState, form: FormData): Promise<SignInState> {
  const email = String(form.get('email') ?? '').trim();
  const password = String(form.get('password') ?? '');
  if (!email || !password) return { error: 'Enter your work email and password.', email };

  const secret = sessionSecret();
  if (!secret) return { error: 'Sign-in is not configured for this deployment.', email };

  const result = await osFetch<{ token: string; expires_at: number }>(null, '/v1/auth/sign-in', {
    method: 'POST',
    body: { email, password },
  });
  if (!result.ok) return { error: result.error, email };

  const claims = await verifySessionToken(result.data.token, secret);
  if (!claims) return { error: 'Vyom OS issued a session this app cannot verify. Check VYOM_SESSION_SECRET.', email };

  const jar = await cookies();
  jar.set(SESSION_COOKIE, result.data.token, {
    ...cookieOptions,
    maxAge: Math.max(60, claims.expiresAt - Math.floor(Date.now() / 1000)),
  });

  const home = homePath(claims.role, claims.tenantSlug);
  redirect(landing(form.get('next'), home, claims.tenantSlug, claims.role === 'ops'));
}

/** Opens the fictional sample workspace as the chosen role. No backend is involved. */
export async function openSampleWorkspace(form: FormData): Promise<void> {
  if (!siteConfig.sampleWorkspace) redirect('/login/');
  const role = form.get('role');
  if (!isRole(role)) redirect('/login/');

  const jar = await cookies();
  jar.set(SESSION_COOKIE, `${SAMPLE_PREFIX}${role}`, { ...cookieOptions, maxAge: SAMPLE_SESSION_SECONDS });

  const home = homePath(role, SAMPLE_TENANT_SLUG);
  redirect(landing(form.get('next'), home, SAMPLE_TENANT_SLUG, role === 'ops'));
}

/** Changes the role inside the sample workspace, keeping the visitor on the same page where allowed. */
export async function switchSampleRole(form: FormData): Promise<void> {
  const jar = await cookies();
  const session = await resolveSession(jar.get(SESSION_COOKIE)?.value);
  const role = form.get('role');
  if (session?.mode !== 'sample' || !isRole(role)) redirect('/login/');

  jar.set(SESSION_COOKIE, `${SAMPLE_PREFIX}${role}`, { ...cookieOptions, maxAge: SAMPLE_SESSION_SECONDS });
  const home = homePath(role, SAMPLE_TENANT_SLUG);
  redirect(landing(form.get('path'), home, SAMPLE_TENANT_SLUG, role === 'ops'));
}

export async function signOut(): Promise<void> {
  const jar = await cookies();
  const session = await resolveSession(jar.get(SESSION_COOKIE)?.value);
  if (session?.mode === 'live') {
    // Records the sign-out in the audit trail; the cookie goes either way.
    await osFetch(
      { token: session.token, tenantId: session.claims.tenantId },
      '/v1/auth/sign-out',
      { method: 'POST' },
    );
  }
  jar.delete(SESSION_COOKIE);
  redirect('/login/');
}
