/**
 * Data access for the console. Pages call these and never talk to Vyom OS or
 * the sample snapshot directly.
 *
 * Live sessions read from Vyom OS with the caller's own token, so the backend
 * enforces tenancy and role policy. Sample sessions read the fictional
 * snapshot with the chosen role's permissions applied.
 */

import 'server-only';
import { cookies } from 'next/headers';
import { notFound, redirect } from 'next/navigation';
import { cache } from 'react';
import { type Session, resolveSession } from '@/lib/auth/resolve';
import { SESSION_COOKIE } from '@/lib/auth/session';
import { type OsCredentials, osFetch } from '@/lib/gateway/api-client';
import type {
  ActivityRow,
  CaseDetail,
  CaseList,
  Dashboard,
  LiteratureDetail,
  LiteratureQueue,
  Me,
  OpsSummary,
  Product,
  ReportDetail,
  ReportListItem,
  TenantSettings,
} from '@/lib/gateway/types';
import * as sample from './sample';

export type Loaded<T> = { readonly ok: true; readonly data: T } | { readonly ok: false; readonly error: string };

export type Workspace = {
  readonly session: Session;
  readonly me: Me;
  readonly today: string;
  readonly sample: boolean;
};

export const getSession = cache(async (): Promise<Session | null> => {
  const jar = await cookies();
  return resolveSession(jar.get(SESSION_COOKIE)?.value);
});

export function credentials(session: Session): OsCredentials | null {
  return session.mode === 'live' ? { token: session.token, tenantId: session.claims.tenantId } : null;
}

/** The signed-in workspace. Sends the visitor to /login when there is no usable session. */
export const getWorkspace = cache(async (): Promise<Workspace> => {
  const session = await getSession();
  if (!session) redirect('/login/');

  if (session.mode === 'sample') {
    const me = sample.sampleMe(session.role);
    return { session, me, today: me.today, sample: true };
  }

  const me = await osFetch<Me>(credentials(session), '/v1/me');
  if (!me.ok) {
    if (me.status === 401) redirect('/login/?expired=1');
    throw new Error(me.error);
  }
  return { session, me: me.data, today: me.data.today, sample: false };
});

async function live<T>(
  path: string,
  query?: Record<string, string | undefined>,
  { missing = 'error' }: { readonly missing?: 'error' | 'notFound' } = {},
): Promise<Loaded<T>> {
  const { session } = await getWorkspace();
  const result = await osFetch<T>(credentials(session), path, { query });
  if (result.ok) return { ok: true, data: result.data };
  if (result.status === 401) redirect('/login/?expired=1');
  if (result.status === 404 && missing === 'notFound') notFound();
  return { ok: false, error: result.error };
}

function found<T>(value: T | null): Loaded<T> {
  if (value === null) notFound();
  return { ok: true, data: value };
}

async function read<T>(
  fromSample: (workspace: Workspace) => T | null,
  path: string,
  query?: Record<string, string | undefined>,
): Promise<Loaded<T>> {
  const workspace = await getWorkspace();
  if (workspace.sample) return found(fromSample(workspace));
  return live<T>(path, query, { missing: 'notFound' });
}

export const loadDashboard = () => read<Dashboard>(() => sample.sampleDashboard(), '/v1/dashboard');

export type LiteratureView = 'open' | 'decided' | 'all';

export const loadLiterature = (view: LiteratureView, product?: string) =>
  read<LiteratureQueue>(() => sample.sampleLiterature(view, product), '/v1/literature', { view, product });

export const loadLiteratureItem = (stateId: string) =>
  read<LiteratureDetail>(
    (w) => sample.sampleLiteratureDetail(stateId, w.session.role),
    `/v1/literature/${encodeURIComponent(stateId)}`,
  );

export const loadCases = (status?: string) =>
  read<CaseList>(() => sample.sampleCases(status), '/v1/cases', { status });

export const loadCase = (caseNumber: string) =>
  read<CaseDetail>((w) => sample.sampleCase(caseNumber, w.session.role), `/v1/cases/${encodeURIComponent(caseNumber)}`);

export const loadReports = () => read<ReportListItem[]>(() => sample.sampleReports(), '/v1/reports');

export const loadReport = (reportNumber: string) =>
  read<ReportDetail>(
    (w) => sample.sampleReport(reportNumber, w.session.role),
    `/v1/reports/${encodeURIComponent(reportNumber)}`,
  );

export const loadProducts = () => read<Product[]>(() => sample.sampleProducts(), '/v1/products');

export const loadSettings = () => read<TenantSettings>(() => sample.sampleSettings(), '/v1/settings');

export const loadAudit = (entityKind?: string, entityRef?: string) =>
  read<ActivityRow[]>(() => sample.sampleAudit(entityKind, entityRef), '/v1/audit', {
    entity_kind: entityKind,
    entity_ref: entityRef,
  });

export const loadOps = () => read<OpsSummary>(() => sample.sampleOps(), '/v1/ops/summary');

/** True when the workspace's permissions include the action. */
export function can(workspace: Workspace, action: string): boolean {
  return workspace.me.permissions.includes(action);
}
