/** Turns the session cookie into a session. Edge-safe; used by the gateway and the server. */

import { siteConfig } from '~/site.config';
import type { Role } from './roles';
import { SAMPLE_TENANT_SLUG, sampleRole } from './session';
import { type SessionClaims, sessionSecret, verifySessionToken } from './token';

export type Session =
  | { readonly mode: 'live'; readonly token: string; readonly claims: SessionClaims; readonly role: Role; readonly tenantSlug: string }
  | { readonly mode: 'sample'; readonly role: Role; readonly tenantSlug: typeof SAMPLE_TENANT_SLUG };

export async function resolveSession(value: string | undefined): Promise<Session | null> {
  if (!value) return null;

  const role = sampleRole(value);
  if (role) {
    return siteConfig.sampleWorkspace ? { mode: 'sample', role, tenantSlug: SAMPLE_TENANT_SLUG } : null;
  }

  const secret = sessionSecret();
  if (!secret) return null;
  const claims = await verifySessionToken(value, secret);
  if (!claims) return null;
  return { mode: 'live', token: value, claims, role: claims.role, tenantSlug: claims.tenantSlug };
}
