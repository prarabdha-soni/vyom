'use server';

/**
 * Console mutations. Each one re-reads the session, so a forged form cannot
 * act for someone else, and Vyom OS enforces role policy again on its side.
 * In the sample workspace nothing is sent anywhere and the caller is told so.
 */

import { refresh } from 'next/cache';
import { redirect } from 'next/navigation';
import { sampleNotSaved } from '@/content/console';
import { osFetch } from '@/lib/gateway/api-client';
import type { CasePayload } from '@/lib/gateway/types';
import { credentials, getSession } from './data';

export type ActionState = {
  readonly status: 'idle' | 'ok' | 'error' | 'sample';
  readonly message: string | null;
  /** What was submitted, returned when the action fails so the form can show it again. */
  readonly fields?: Readonly<Record<string, string>>;
};

/** Typed values from a form, minus secrets and React's own entries. */
function kept(form: FormData): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const [key, value] of form.entries()) {
    if (typeof value === 'string' && key !== 'password' && !key.startsWith('$')) fields[key] = value;
  }
  return fields;
}

const text = (form: FormData, key: string) => String(form.get(key) ?? '').trim();
const int = (form: FormData, key: string) => Number.parseInt(text(form, key), 10);
const segment = (value: string) => encodeURIComponent(value);

type Mutation = {
  readonly path: string;
  /** The submitted form; its values come back with an error so nothing typed is lost. */
  readonly form?: FormData;
  readonly method?: 'POST' | 'PUT';
  readonly body?: unknown;
  readonly success?: string;
};

/** Runs a mutation for the current session. Returns state, or the parsed response via `then`. */
async function mutate<T = unknown>(
  { path, method = 'POST', body, form, success = 'Saved.' }: Mutation,
  then?: (data: T, tenantSlug: string) => string | void,
): Promise<ActionState> {
  const session = await getSession();
  if (!session) redirect('/login/');
  if (session.mode === 'sample') return { status: 'sample', message: sampleNotSaved, fields: form ? kept(form) : undefined };

  const result = await osFetch<T>(credentials(session), path, { method, body });
  if (!result.ok) {
    if (result.status === 401) redirect('/login/?expired=1');
    return { status: 'error', message: result.error, fields: form ? kept(form) : undefined };
  }
  const destination = then?.(result.data, session.tenantSlug);
  if (destination) redirect(destination);
  refresh();
  return { status: 'ok', message: success };
}

// ---------------------------------------------------------------------------
// Radar
// ---------------------------------------------------------------------------

export async function decideLiterature(_previous: ActionState, form: FormData): Promise<ActionState> {
  const stateId = text(form, 'state_id');
  const next = text(form, 'next');
  return mutate<{ case_number?: string | null }>(
    {
      path: `/v1/literature/${segment(stateId)}/decision`,
      form,
      body: { decision_id: int(form, 'decision_id'), outcome: text(form, 'outcome'), reason: text(form, 'reason') || null },
      success: 'Decision recorded.',
    },
    (_data, tenant) => (next ? `/${tenant}/radar/${segment(next)}/` : undefined),
  );
}

export async function runSweep(): Promise<ActionState> {
  return mutate<{ screened?: number }>({ path: '/v1/literature/sweeps', body: {}, success: 'Sweep complete.' });
}

// ---------------------------------------------------------------------------
// Verify
// ---------------------------------------------------------------------------

export async function createCase(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate<{ case_number: string }>(
    {
      path: '/v1/cases',
      form,
      body: {
        channel: text(form, 'channel'),
        subject: text(form, 'subject') || null,
        received_on: text(form, 'received_on') || null,
        source_text: text(form, 'source_text'),
      },
    },
    (data, tenant) => `/${tenant}/verify/${segment(data.case_number)}/`,
  );
}

export async function saveCase(_previous: ActionState, form: FormData): Promise<ActionState> {
  let payload: CasePayload;
  try {
    payload = JSON.parse(text(form, 'payload')) as CasePayload;
  } catch {
    return { status: 'error', message: 'The form could not be read. Reload and try again.', fields: kept(form) };
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { status: 'error', message: 'The form could not be read. Reload and try again.' };
  }
  const caseNumber = text(form, 'case_number');
  const tab = text(form, 'return_tab');
  return mutate(
    {
      path: `/v1/cases/${segment(caseNumber)}`,
      method: 'PUT',
      form,
      body: { expected_version: int(form, 'expected_version'), payload, reason: text(form, 'reason') },
      success: 'New version saved.',
    },
    (_data, tenant) => `/${tenant}/verify/${segment(caseNumber)}/${tab === 'narrative' ? '?tab=narrative' : ''}`,
  );
}

export async function draftNarrative(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate({
    path: `/v1/cases/${segment(text(form, 'case_number'))}/narrative`,
    body: { expected_version: int(form, 'expected_version') },
    success: 'Narrative drafted. Review it before approval.',
  });
}

export async function transitionCase(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate({
    path: `/v1/cases/${segment(text(form, 'case_number'))}/transitions`,
    form,
    body: {
      action: text(form, 'action'),
      expected_version: int(form, 'expected_version'),
      reason: text(form, 'reason') || null,
      duplicate_of: text(form, 'duplicate_of') || null,
    },
    success: 'Status updated.',
  });
}

export async function exportCase(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate({
    path: `/v1/cases/${segment(text(form, 'case_number'))}/exports`,
    success: 'E2B export created.',
  });
}

// ---------------------------------------------------------------------------
// Dossier
// ---------------------------------------------------------------------------

export async function createReport(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate<{ report_number: string }>(
    {
      path: '/v1/reports',
      form,
      body: {
        product_code: text(form, 'product_code'),
        report_type: text(form, 'report_type'),
        interval_start: text(form, 'interval_start'),
        data_lock_point: text(form, 'data_lock_point'),
      },
    },
    (data, tenant) => `/${tenant}/dossier/${segment(data.report_number)}/`,
  );
}

export async function updateSection(_previous: ActionState, form: FormData): Promise<ActionState> {
  const action = text(form, 'action');
  return mutate({
    path: `/v1/reports/${segment(text(form, 'report_number'))}/sections/${segment(text(form, 'key'))}`,
    form,
    body: {
      expected_version: int(form, 'expected_version'),
      action,
      text: action === 'edit' ? String(form.get('text') ?? '') : null,
      reason: text(form, 'reason') || null,
    },
    success: action === 'accept' ? 'Draft accepted.' : 'Section saved.',
  });
}

export async function signOffReport(_previous: ActionState, form: FormData): Promise<ActionState> {
  return mutate({
    path: `/v1/reports/${segment(text(form, 'report_number'))}/signoff`,
    body: { version: int(form, 'version'), meaning: text(form, 'meaning'), password: String(form.get('password') ?? '') },
    success: 'Report signed off.',
  });
}
