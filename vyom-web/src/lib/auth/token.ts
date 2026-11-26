/**
 * Verifies Vyom OS session tokens with WebCrypto, so it runs in the edge
 * gateway and in server components alike.
 *
 * The token is HS256 over the UTF-8 bytes of VYOM_SESSION_SECRET, which Vyom OS
 * and this app share. Header, issuer, audience, expiry and the role are all
 * checked, mirroring `vyom_os.security.verify_token`.
 */

import { isRole, type Role } from './roles';

export const TOKEN_ISSUER = 'vyom-os';
export const TOKEN_AUDIENCE = 'vyom-console';

export type SessionClaims = {
  readonly userId: string;
  readonly email: string;
  readonly role: Role;
  readonly tenantId: string;
  readonly tenantSlug: string;
  readonly issuedAt: number;
  readonly expiresAt: number;
};

const encoder = new TextEncoder();
const keyCache = new Map<string, Promise<CryptoKey>>();

function hmacKey(secret: string): Promise<CryptoKey> {
  let key = keyCache.get(secret);
  if (!key) {
    key = crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, [
      'verify',
    ]);
    keyCache.set(secret, key);
  }
  return key;
}

function base64UrlBytes(text: string): Uint8Array<ArrayBuffer> {
  if (!/^[A-Za-z0-9_-]*$/.test(text)) throw new Error('not base64url');
  const padded = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function base64UrlJson(text: string): unknown {
  return JSON.parse(new TextDecoder().decode(base64UrlBytes(text)));
}

/** The configured secret, or null when it is missing or too short to be safe. */
export function sessionSecret(): string | null {
  const secret = process.env.VYOM_SESSION_SECRET;
  return secret && secret.length >= 32 ? secret : null;
}

/** Claims for a valid token, or null for anything malformed, tampered with or expired. */
export async function verifySessionToken(
  token: string,
  secret: string,
  now: number = Math.floor(Date.now() / 1000),
): Promise<SessionClaims | null> {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [headerPart, payloadPart, signaturePart] = parts as [string, string, string];

  try {
    const header = base64UrlJson(headerPart) as Record<string, unknown>;
    if (Object.keys(header).length !== 2 || header.alg !== 'HS256' || header.typ !== 'JWT') return null;

    const valid = await crypto.subtle.verify(
      'HMAC',
      await hmacKey(secret),
      base64UrlBytes(signaturePart),
      encoder.encode(`${headerPart}.${payloadPart}`),
    );
    if (!valid) return null;

    const payload = base64UrlJson(payloadPart) as Record<string, unknown>;
    if (payload.iss !== TOKEN_ISSUER || payload.aud !== TOKEN_AUDIENCE) return null;
    const { sub, email, role, tid, tsl, iat, exp } = payload;
    if (
      typeof sub !== 'string' ||
      typeof email !== 'string' ||
      !isRole(role) ||
      typeof tid !== 'string' ||
      typeof tsl !== 'string' ||
      typeof iat !== 'number' ||
      typeof exp !== 'number'
    ) {
      return null;
    }
    if (now >= exp || iat > now + 60) return null;

    return { userId: sub, email, role, tenantId: tid, tenantSlug: tsl, issuedAt: iat, expiresAt: exp };
  } catch {
    return null;
  }
}
