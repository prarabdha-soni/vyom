/**
 * Server-side client for Vyom OS (FastAPI). Tenant-app calls to the backend go
 * through here and nowhere else.
 *
 * Every request carries the session token as a Bearer credential and the
 * token's tenant id as X-Tenant-ID; Vyom OS rejects a mismatch. The token
 * never reaches the browser: it lives in an httpOnly cookie and is read on
 * the server only.
 */

import 'server-only';

export type OsResult<T> =
  | { readonly ok: true; readonly data: T; readonly headers: Headers }
  | { readonly ok: false; readonly status: number; readonly error: string };

export type OsCredentials = { readonly token: string; readonly tenantId: string };

/** Base URL of Vyom OS, or null when this deployment runs without a backend. */
export function osBaseUrl(): string | null {
  const url = process.env.VYOM_OS_URL?.trim();
  return url ? url.replace(/\/$/, '') : null;
}

/** FastAPI returns `detail` as a string for domain errors and as a list for validation errors. */
function errorText(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const { detail } = body as { detail: unknown };
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String((item as { msg: unknown }).msg) : null))
        .filter(Boolean);
      if (messages.length) return messages.join(' ');
    }
  }
  if (status === 401) return 'Your session has ended. Sign in again.';
  if (status === 403) return 'Your role does not allow this.';
  if (status === 404) return 'Not found.';
  return `Vyom OS returned an error (${status}).`;
}

type OsRequest = {
  readonly method?: 'GET' | 'POST' | 'PUT';
  readonly body?: unknown;
  readonly query?: Record<string, string | number | undefined | null>;
  /** Return the raw text instead of parsing JSON (exports). */
  readonly text?: boolean;
};

export async function osFetch<T>(
  credentials: OsCredentials | null,
  path: string,
  { method = 'GET', body, query, text = false }: OsRequest = {},
): Promise<OsResult<T>> {
  const base = osBaseUrl();
  if (!base) return { ok: false, status: 503, error: 'Vyom OS is not configured for this deployment.' };

  const url = new URL(`${base}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  }

  const headers = new Headers({ accept: text ? '*/*' : 'application/json' });
  if (body !== undefined) headers.set('content-type', 'application/json');
  if (credentials) {
    headers.set('authorization', `Bearer ${credentials.token}`);
    headers.set('x-tenant-id', credentials.tenantId);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return { ok: false, status: 503, error: 'Could not reach Vyom OS. Try again in a moment.' };
  }

  if (!response.ok) {
    const parsed: unknown = await response.json().catch(() => null);
    return { ok: false, status: response.status, error: errorText(parsed, response.status) };
  }

  const data = (text ? await response.text() : await response.json()) as T;
  return { ok: true, data, headers: response.headers };
}
