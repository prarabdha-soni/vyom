/**
 * The sample workspace: the fictional tenant demo-pharma, captured from a
 * running Vyom OS (see content/sample-workspace/README.md) and served without
 * a backend.
 *
 * Every date in the capture moves forward by the days since it was taken, so
 * the workspace always reads as current and reporting clocks stay consistent.
 * Character offsets that point into shifted text (evidence quotes, keyword
 * highlights) are remapped to match. Permissions follow the role the visitor
 * chose, using the captured policy table.
 */

import 'server-only';
import { createHash } from 'node:crypto';
import snapshotJson from '@/content/sample-workspace/snapshot.json';
import type { Role } from '@/lib/auth/roles';
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

type Snapshot = {
  captured_on: string;
  me: Partial<Record<Role, Me>>;
  dashboard: Dashboard;
  products: Product[];
  settings: TenantSettings;
  audit: ActivityRow[];
  ops: OpsSummary;
  literature: LiteratureQueue;
  literature_detail: Record<string, LiteratureDetail>;
  cases: CaseList;
  case_detail: Record<string, CaseDetail>;
  case_exports: Record<string, { xml: string; sha256: string | null }>;
  reports: ReportListItem[];
  report_detail: Record<string, ReportDetail>;
  report_markdown: Record<string, string>;
};

const captured = snapshotJson as unknown as Snapshot;

// ---------------------------------------------------------------------------
// Date shifting
// ---------------------------------------------------------------------------

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;

/** ISO dates (also inside timestamps) and long dates such as "13 November 2026". */
const DATE_PATTERN = new RegExp(
  `(?<![0-9])(\\d{4})-(\\d{2})-(\\d{2})(?![0-9])|(?<![0-9])(\\d{1,2}) (${MONTHS.join('|')}) (\\d{4})(?![0-9])`,
  'g',
);
/** Compact dates in E2B XML, such as 20261127. */
const COMPACT_DATE = /(?<![0-9])(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?![0-9])/g;

function addDays(year: number, monthIndex: number, day: number, days: number): Date {
  return new Date(Date.UTC(year, monthIndex, day + days));
}

const pad = (value: number) => String(value).padStart(2, '0');

type Shifted = { readonly text: string; readonly map: (offset: number) => number };

function shiftText(text: string, days: number): Shifted {
  if (days === 0) return { text, map: (offset) => offset };
  const edits: { end: number; delta: number }[] = [];
  const out = text.replace(DATE_PATTERN, (match, y, m, d, longDay, longMonth, longYear, offset: number) => {
    let next: string;
    if (y) {
      const date = addDays(Number(y), Number(m) - 1, Number(d), days);
      next = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
    } else {
      const date = addDays(Number(longYear), MONTHS.indexOf(longMonth), Number(longDay), days);
      next = `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
    }
    if (next.length !== match.length) edits.push({ end: offset + match.length, delta: next.length - match.length });
    return next;
  });
  return {
    text: out,
    map: (offset) => offset + edits.reduce((sum, edit) => (edit.end <= offset ? sum + edit.delta : sum), 0),
  };
}

function shiftXml(xml: string, days: number): string {
  const iso = shiftText(xml, days).text;
  return iso.replace(COMPACT_DATE, (_match, y, m, d) => {
    const date = addDays(Number(y), Number(m) - 1, Number(d), days);
    return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}`;
  });
}

function deepShift<T>(value: T, days: number): T {
  if (typeof value === 'string') return shiftText(value, days).text as T;
  if (Array.isArray(value)) return value.map((item) => deepShift(item, days)) as T;
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, deepShift(item, days)])) as T;
  }
  return value;
}

/** Today's date in the sample tenant's time zone, as YYYY-MM-DD. */
export function sampleToday(): string {
  const zone = captured.settings.timezone ?? 'Asia/Kolkata';
  return new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(),
  );
}

function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);
}

function sha256(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

function build(days: number): Snapshot {
  const shifted = deepShift(captured, days);

  // Offsets were measured on the captured text; move them with the dates.
  for (const [id, detail] of Object.entries(captured.literature_detail)) {
    const target = shifted.literature_detail[id];
    if (!target) continue;
    const title = shiftText(detail.title, days);
    const abstract = shiftText(detail.abstract ?? '', days);
    (target as { highlights: LiteratureDetail['highlights'] }).highlights = {
      ...target.highlights,
      title: detail.highlights.title.map((h) => ({ ...h, start: title.map(h.start), end: title.map(h.end) })),
      abstract: detail.highlights.abstract.map((h) => ({ ...h, start: abstract.map(h.start), end: abstract.map(h.end) })),
    };
  }
  for (const [number, detail] of Object.entries(captured.case_detail)) {
    const target = shifted.case_detail[number];
    if (!target) continue;
    const source = shiftText(detail.source.text ?? '', days);
    target.payload.evidence = Object.fromEntries(
      Object.entries(detail.payload.evidence ?? {}).map(([key, evidence]) => [
        key,
        {
          ...evidence,
          quote: shiftText(evidence.quote, days).text,
          start: source.map(evidence.start),
          end: source.map(evidence.end),
        },
      ]),
    );
  }

  // Exports are sealed by hash; reseal the shifted XML so the hash stays true.
  for (const [key, exported] of Object.entries(captured.case_exports)) {
    const xml = shiftXml(exported.xml, days);
    const digest = sha256(xml);
    shifted.case_exports[key] = { xml, sha256: digest };
    const [number, id] = key.split('/');
    const detail = number ? shifted.case_detail[number] : undefined;
    if (detail) {
      (detail as { exports: CaseDetail['exports'] }).exports = detail.exports.map((row) =>
        String(row.id) === id ? { ...row, content_sha256: digest } : row,
      );
    }
  }
  return shifted;
}

let memo: { readonly days: number; readonly data: Snapshot } | null = null;

function workspace(): Snapshot {
  const days = daysBetween(captured.captured_on, sampleToday());
  if (memo?.days !== days) memo = { days, data: build(days) };
  return memo.data;
}

// ---------------------------------------------------------------------------
// Role-aware reads
// ---------------------------------------------------------------------------

function allowed(role: Role, action: string): boolean {
  return (captured.settings.permissions[role] ?? []).includes(action);
}

const OPEN_CASE = new Set(['data_entry', 'medical_review']);

export function sampleMe(role: Role): Me {
  const data = workspace();
  const base = data.me[role] ?? data.me.reviewer;
  if (!base) throw new Error('Sample workspace has no users.');
  if (data.me[role]) return { ...base, today: sampleToday() };
  return {
    ...base,
    user: { id: 'sample-ops', email: 'ops@vyom-internal.example', role },
    permissions: data.settings.permissions[role] ?? [],
    today: sampleToday(),
  };
}

export const sampleDashboard = (): Dashboard => ({ ...workspace().dashboard, today: sampleToday() });

export function sampleLiterature(view: 'open' | 'decided' | 'all', product?: string): LiteratureQueue {
  const { literature } = workspace();
  const items = literature.items.filter((item) => {
    const open = item.outcome === null || item.outcome === 'escalated';
    if (view === 'open' && !open) return false;
    if (view === 'decided' && open) return false;
    return !product || item.products.includes(product);
  });
  return { items, counts: literature.counts };
}

export function sampleLiteratureDetail(stateId: string, role: Role): LiteratureDetail | null {
  const detail = workspace().literature_detail[stateId];
  if (!detail) return null;
  // Mirrors Vyom OS: once escalated, only a safety physician (or above) may close the article.
  const awaiting = detail.final_outcome === null && detail.outcomes[0]?.outcome === 'escalated';
  return {
    ...detail,
    awaiting_physician: awaiting,
    can_decide: allowed(role, 'literature.screen') && detail.final_outcome === null && !(awaiting && role === 'reviewer'),
  };
}

export function sampleCases(status?: string): CaseList {
  const { cases } = workspace();
  const items = cases.items.filter((item) =>
    status === 'open' ? OPEN_CASE.has(item.status) : status ? item.status === status : true,
  );
  return { items, counts: cases.counts };
}

export function sampleCase(caseNumber: string, role: Role): CaseDetail | null {
  const detail = workspace().case_detail[caseNumber];
  if (!detail) return null;
  const open = OPEN_CASE.has(detail.case.status);
  return {
    ...detail,
    permissions: {
      edit: allowed(role, 'case.edit') && open,
      assess_causality: allowed(role, 'case.assess_causality') && open,
      submit: allowed(role, 'case.submit'),
      approve: allowed(role, 'case.approve') && (!detail.case.serious || allowed(role, 'case.approve_serious')),
      export: allowed(role, 'case.export'),
    },
  };
}

export function sampleCaseExport(caseNumber: string, exportId: string): { xml: string; sha256: string | null } | null {
  return workspace().case_exports[`${caseNumber}/${exportId}`] ?? null;
}

export const sampleReports = (): ReportListItem[] => workspace().reports;

export function sampleReport(reportNumber: string, role: Role): ReportDetail | null {
  const detail = workspace().report_detail[reportNumber];
  if (!detail) return null;
  const draft = detail.report.status === 'draft';
  return {
    ...detail,
    permissions: { edit: allowed(role, 'report.edit') && draft, signoff: allowed(role, 'report.signoff') && draft },
  };
}

export const sampleReportMarkdown = (reportNumber: string): string | null =>
  workspace().report_markdown[reportNumber] ?? null;

export const sampleProducts = (): Product[] => workspace().products;
export const sampleSettings = (): TenantSettings => workspace().settings;
export const sampleOps = (): OpsSummary => workspace().ops;

export function sampleAudit(entityKind?: string, entityRef?: string): ActivityRow[] {
  return workspace().audit.filter(
    (row) => (!entityKind || row.entity_kind === entityKind) && (!entityRef || row.entity_ref === entityRef),
  );
}

export const samplePermissions = (role: Role): readonly string[] => captured.settings.permissions[role] ?? [];
