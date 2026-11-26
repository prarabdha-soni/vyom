/**
 * Shared console pieces. Colour follows the semantic rule: blue only for AI,
 * amber for a human decision, green for verified or complete, rose for
 * locked or overdue. Rule-based output stays neutral.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';
import {
  bandLabel,
  caseStatusLabel,
  clockStatusLabel,
  engineCopy,
  eventVerb,
  outcomeLabel,
  SECTION_DONE,
  sectionStatusLabel,
  systemActor,
} from '@/content/console';
import { AlertIcon, ArrowRightIcon, ChevronRightIcon } from '@/components/icons';
import { Chip } from '@/components/ui';
import { cn } from '@/lib/cn';
import { formatDateTime, shortEmail } from '@/lib/console/format';
import type { Clock, FeedRow } from '@/lib/gateway/types';

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export type Crumb = { readonly label: string; readonly href?: string };

export function PageHeader({
  crumbs,
  title,
  lead,
  meta,
  actions,
  children,
}: {
  readonly crumbs?: readonly Crumb[];
  readonly title: ReactNode;
  readonly lead?: ReactNode;
  readonly meta?: ReactNode;
  readonly actions?: ReactNode;
  readonly children?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 border-b border-hairline bg-surface px-4 pt-5 pb-4 sm:px-6 lg:px-8">
      {crumbs?.length ? (
        <nav aria-label="Breadcrumb">
          <ol className="m-0 flex list-none flex-wrap items-center gap-1 p-0 text-[13px] text-meta">
            {crumbs.map((crumb, index) => (
              <li key={`${crumb.label}-${index}`} className="flex items-center gap-1">
                {index > 0 ? <ChevronRightIcon size={13} className="text-dash" /> : null}
                {crumb.href ? (
                  <Link href={crumb.href} className="rounded px-0.5 hover:text-primary hover:underline">
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="px-0.5 text-secondary">
                    {crumb.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      ) : null}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <h1 className="m-0 flex flex-wrap items-center gap-x-3 gap-y-2 text-[24px] leading-[1.15] font-semibold tracking-[-0.025em] text-primary sm:text-[26px]">
            {title}
          </h1>
          {lead ? <p className="m-0 max-w-[720px] text-[14.5px] leading-[1.5] text-muted">{lead}</p> : null}
          {meta ? <div className="mt-1 flex flex-wrap items-center gap-2">{meta}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </header>
  );
}

export function PageBody({ children, className }: { readonly children: ReactNode; readonly className?: string }) {
  return <div className={cn('flex flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8 lg:py-6', className)}>{children}</div>;
}

export function Panel({
  title,
  lead,
  action,
  children,
  className,
  bodyClassName,
  headingLevel = 2,
}: {
  readonly title?: ReactNode;
  readonly lead?: ReactNode;
  readonly action?: { readonly label: string; readonly href: string } | ReactNode;
  readonly children: ReactNode;
  readonly className?: string;
  readonly bodyClassName?: string;
  readonly headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 2 ? 'h2' : 'h3';
  const link = action && typeof action === 'object' && 'href' in action ? action : null;
  return (
    <section className={cn('flex min-w-0 flex-col rounded-card border border-line bg-surface', className)}>
      {title ? (
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 border-b border-hairline px-4 py-3 sm:px-5">
          <div className="flex min-w-0 flex-col gap-0.5">
            <Heading className="m-0 text-[15px] font-semibold tracking-[-0.01em] text-primary">{title}</Heading>
            {lead ? <p className="m-0 text-[13px] leading-[1.45] text-meta">{lead}</p> : null}
          </div>
          {link ? (
            <Link
              href={link.href}
              className="inline-flex min-h-[32px] items-center gap-1 text-[13px] font-medium text-secondary hover:text-primary hover:underline"
            >
              {link.label}
              <ArrowRightIcon size={13} />
            </Link>
          ) : (
            (action as ReactNode)
          )}
        </div>
      ) : null}
      <div className={cn('min-w-0 flex-1 p-4 sm:p-5', bodyClassName)}>{children}</div>
    </section>
  );
}

/** A segmented control made of links, so each view has its own URL. */
export function SegmentedTabs({
  label,
  items,
  className,
}: {
  readonly label: string;
  readonly items: readonly { readonly label: string; readonly href: string; readonly active: boolean; readonly count?: number }[];
  readonly className?: string;
}) {
  return (
    <nav aria-label={label} className={cn('max-w-full overflow-x-auto', className)}>
      <ul className="m-0 inline-flex list-none gap-0.5 rounded-button bg-raised p-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={item.active ? 'page' : undefined}
              className={cn(
                'flex min-h-[34px] items-center gap-2 rounded-control px-3.5 text-[13.5px] font-medium whitespace-nowrap transition-colors',
                item.active ? 'bg-surface text-primary shadow-tab' : 'text-muted hover:text-primary',
              )}
            >
              {item.label}
              {item.count !== undefined ? (
                <span className={cn('font-mono text-[11px]', item.active ? 'text-secondary' : 'text-meta')}>{item.count}</span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Kpi({
  label,
  value,
  detail,
  href,
  emphasis = false,
}: {
  readonly label: string;
  readonly value: ReactNode;
  readonly detail?: ReactNode;
  readonly href?: string;
  readonly emphasis?: boolean;
}) {
  const body = (
    <>
      <span className="text-[13px] leading-[1.35] text-muted">{label}</span>
      <span
        className={cn(
          'text-[34px] leading-none font-semibold tracking-[-0.03em] tabular-nums',
          emphasis ? 'text-rose' : 'text-primary',
        )}
      >
        {value}
      </span>
      {detail ? <span className="text-[12.5px] text-meta">{detail}</span> : null}
    </>
  );
  const classes = 'flex min-w-0 flex-col gap-2.5 rounded-card border border-line bg-surface p-4 sm:p-5';
  return href ? (
    <Link href={href} className={cn(classes, 'transition-colors hover:border-strong hover:bg-panel-header')}>
      {body}
    </Link>
  ) : (
    <div className={classes}>{body}</div>
  );
}

export function KeyValues({
  items,
  columns = 2,
}: {
  readonly items: readonly { readonly label: string; readonly value: ReactNode }[];
  readonly columns?: 1 | 2 | 3;
}) {
  return (
    <dl
      className={cn(
        'm-0 grid gap-x-6 gap-y-3.5',
        columns === 1 ? 'grid-cols-1' : columns === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3',
      )}
    >
      {items.map((item) => (
        <div key={item.label} className="flex min-w-0 flex-col gap-1">
          <dt className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{item.label}</dt>
          <dd className="m-0 text-[14px] leading-[1.45] break-words text-primary">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function EmptyState({ children }: { readonly children: ReactNode }) {
  return (
    <p className="m-0 rounded-nested border border-dashed border-strong px-4 py-6 text-center text-[14px] text-muted">
      {children}
    </p>
  );
}

export function LoadFailed({ error }: { readonly error: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-card border border-rose-line bg-rose-soft p-4 text-[14px] text-rose">
      <AlertIcon className="mt-0.5 shrink-0" />
      <p className="m-0">{error}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------

export const th = 'border-b border-line bg-panel-header px-3 py-2.5 text-left font-mono text-[11px] font-medium tracking-[0.08em] whitespace-nowrap text-meta uppercase first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5';
export const td = 'border-b border-hairline px-3 py-3 align-top text-[14px] text-secondary first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5';

// ---------------------------------------------------------------------------
// Status chips
// ---------------------------------------------------------------------------

export function CaseStatusChip({ status }: { readonly status: string }) {
  const tone = status === 'approved' ? 'green' : status === 'medical_review' ? 'default' : 'muted';
  return (
    <Chip tone={tone} size="sm">
      {(caseStatusLabel[status] ?? status).toUpperCase()}
    </Chip>
  );
}

/** Screening bands are rule or model output, never a human decision: neutral ink only. */
export function BandChip({ band }: { readonly band: string | null }) {
  if (!band) return null;
  const strength = band.startsWith('RED') ? 'bg-primary' : band.startsWith('YELLOW') ? 'bg-dash' : 'bg-strong';
  return (
    <span className="inline-flex items-center gap-1.5 rounded-chip border border-strong px-2 py-1 font-mono text-[11px] font-medium tracking-[0.08em] whitespace-nowrap text-secondary">
      <span aria-hidden="true" className={cn('size-2 rounded-full', strength)} />
      {bandLabel[band] ?? band.replace(/_/g, ' · ')}
    </span>
  );
}

/** A literature decision is a human decision: amber. */
export function OutcomeChip({ outcome }: { readonly outcome: string }) {
  return (
    <Chip tone="amber" size="sm">
      {(outcomeLabel[outcome] ?? outcome).toUpperCase()}
    </Chip>
  );
}

export function ClockChip({ clock }: { readonly clock: Clock }) {
  const tone = clock.status === 'overdue' ? 'rose' : clock.status === 'stopped' ? 'muted' : 'default';
  return (
    <Chip tone={tone} size="sm">
      {clock.status === 'stopped' ? (clockStatusLabel.stopped ?? clock.label).toUpperCase() : clock.label.toUpperCase()}
    </Chip>
  );
}

export function SectionStatusChip({ status }: { readonly status: string }) {
  const tone = SECTION_DONE.has(status) ? 'green' : status === 'draft' ? 'default' : 'dashed';
  return (
    <Chip tone={tone} size="sm">
      {(sectionStatusLabel[status] ?? status).toUpperCase()}
    </Chip>
  );
}

/** Blue only when a model actually produced the output. */
export function EngineChip({ isAi, model }: { readonly isAi: boolean; readonly model?: string | null }) {
  return (
    <Chip tone={isAi ? 'accent' : 'muted'} size="sm">
      {isAi ? engineCopy.ai : engineCopy.ruleBased}
      {model ? <span className="ml-1.5 tracking-normal normal-case opacity-80">{model}</span> : null}
    </Chip>
  );
}

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

type ActivityGroup = { readonly row: FeedRow; readonly count: number; readonly actors: readonly string[] };

/** Consecutive identical events on one record collapse into a single line. */
function groupActivity(rows: readonly FeedRow[]): ActivityGroup[] {
  const groups: ActivityGroup[] = [];
  for (const row of rows) {
    const last = groups.at(-1);
    const actor = shortEmail(row.actor_email) || systemActor;
    if (last && last.row.event_type === row.event_type && last.row.entity_ref === row.entity_ref) {
      groups[groups.length - 1] = {
        row: last.row,
        count: last.count + 1,
        actors: last.actors.includes(actor) ? last.actors : [...last.actors, actor],
      };
    } else {
      groups.push({ row, count: 1, actors: [actor] });
    }
  }
  return groups;
}

export function entityHref(tenantSlug: string, kind: string, ref: string): string | null {
  if (kind === 'case') return `/${tenantSlug}/verify/${encodeURIComponent(ref)}/`;
  if (kind === 'report') return `/${tenantSlug}/dossier/${encodeURIComponent(ref)}/`;
  if (kind === 'literature' && /^\d+$/.test(ref)) return `/${tenantSlug}/radar/${ref}/`;
  return null;
}

export function entityLabel(kind: string, ref: string): string | null {
  if (kind === 'literature') return /^\d+$/.test(ref) ? `article ${ref}` : null;
  if (kind === 'user' || kind === 'product') return null;
  return ref;
}

export function ActivityFeed({
  rows,
  tenantSlug,
  empty,
}: {
  readonly rows: readonly FeedRow[];
  readonly tenantSlug: string;
  readonly empty: string;
}) {
  if (!rows.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ol className="m-0 flex list-none flex-col p-0">
      {groupActivity(rows).map(({ row, count, actors }, index) => {
        const kind = row.entity_kind ?? '';
        const ref = row.entity_ref ?? '';
        const href = ref ? entityHref(tenantSlug, kind, ref) : null;
        const label = ref ? entityLabel(kind, ref) : null;
        const reason = typeof row.detail?.reason === 'string' ? row.detail.reason : null;
        const section = typeof row.detail?.section === 'string' ? row.detail.section : null;
        return (
          <li
            key={`${row.created_at}-${index}`}
            className="flex gap-3 border-b border-hairline py-2.5 text-[13.5px] leading-[1.45] last:border-b-0"
          >
            <span aria-hidden="true" className="mt-[7px] size-1.5 shrink-0 rounded-full bg-dash" />
            <span className="min-w-0 flex-1 text-secondary">
              <span className="font-medium text-primary">{actors.join(' and ')}</span>{' '}
              {eventVerb[row.event_type] ?? row.event_type.replace(/_/g, ' ')}{' '}
              {label ? (
                href ? (
                  <Link href={href} className="font-mono text-[12.5px] text-primary underline-offset-2 hover:underline">
                    {label}
                  </Link>
                ) : (
                  <span className="font-mono text-[12.5px]">{label}</span>
                )
              ) : null}
              {section ? <span className="font-mono text-[12px] text-meta"> · {section.replace(/_/g, ' ')}</span> : null}
              {count > 1 ? <span className="text-meta"> · {count} times</span> : null}
              {reason ? <span className="mt-0.5 block text-[13px] text-meta">{reason}</span> : null}
            </span>
            <time dateTime={row.created_at} className="shrink-0 font-mono text-[11.5px] text-meta">
              {formatDateTime(row.created_at)}
            </time>
          </li>
        );
      })}
    </ol>
  );
}
