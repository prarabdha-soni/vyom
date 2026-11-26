import type { Metadata } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { SECTION_DONE, dossierCopy, reportStatusLabel, reportTypeLabel, sampleComments, sectionGuidance } from '@/content/console';
import { AcceptSection, SectionEditor, SignOffForm } from '@/components/console/dossier/DossierControls';
import {
  ActivityFeed,
  EmptyState,
  EngineChip,
  KeyValues,
  LoadFailed,
  PageBody,
  PageHeader,
  Panel,
  SectionStatusChip,
  SegmentedTabs,
  td,
  th,
} from '@/components/console/ui';
import { AlertIcon, DashedCircleIcon, DownloadIcon, HalfCircleIcon, LockIcon, PencilIcon, StepCheckIcon } from '@/components/icons';
import { ButtonLink, Chip, ProgressBar, ScrollableTable } from '@/components/ui';
import { cn } from '@/lib/cn';
import { isRole, roleLabel } from '@/lib/auth/roles';
import { getWorkspace, loadReport } from '@/lib/console/data';
import { formatCount, formatDate, formatDateTime, shortEmail } from '@/lib/console/format';
import type { ReportDetail, ReportSection } from '@/lib/gateway/types';

export async function generateMetadata({ params }: PageProps<'/[tenant_slug]/dossier/[reportNumber]'>): Promise<Metadata> {
  const { reportNumber } = await params;
  return { title: decodeURIComponent(reportNumber) };
}

const copy = dossierCopy.workspace;
const CASE_REFERENCE = /(\b[A-Z]+-CASE-\d+\b)/g;

function isDone(status: string) {
  return SECTION_DONE.has(status);
}

function StatusIcon({ status }: { readonly status: string }) {
  if (isDone(status)) return <StepCheckIcon size={16} className="shrink-0 text-green" />;
  if (status === 'draft') return <HalfCircleIcon size={16} className="shrink-0 text-secondary" />;
  return <DashedCircleIcon size={16} className="shrink-0 text-dash" />;
}

/** Case numbers in drafted text link back to the case they came from. */
function TraceableText({ text, tenantSlug }: { readonly text: string; readonly tenantSlug: string }) {
  return (
    <>
      {text.split('\n').filter(Boolean).map((paragraph, index) => (
        <p key={index} className="m-0 text-[15px] leading-[1.75] text-secondary">
          {paragraph.split(CASE_REFERENCE).map((part, partIndex) =>
            /^[A-Z]+-CASE-\d+$/.test(part) ? (
              <Link
                key={partIndex}
                href={`/${tenantSlug}/verify/${part}/`}
                className="rounded-[3px] bg-green-soft px-0.5 font-mono text-[13.5px] text-green underline decoration-green-line underline-offset-2 hover:decoration-green"
              >
                {part}
              </Link>
            ) : (
              part
            ),
          )}
        </p>
      ))}
    </>
  );
}

function SectionTables({ section }: { readonly section: ReportSection }) {
  return (
    <>
      {section.tables.map((table) => (
        <div key={table.title} className="flex flex-col gap-2">
          <span className="text-[13px] font-medium text-primary">{table.title}</span>
          <div className="rounded-nested border border-line">
            <ScrollableTable label={table.title}>
              <table className="w-full min-w-[520px] border-collapse">
                <thead>
                  <tr>
                    {table.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.length ? (
                    table.rows.map((row, index) => (
                      <tr key={index}>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} className={`${td} text-[13.5px]`}>
                            {cell === null || cell === '' ? '—' : String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={table.columns.length} className={`${td} text-center text-meta`}>
                        —
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </ScrollableTable>
          </div>
        </div>
      ))}
    </>
  );
}

function Disclosure({ title, meta, children }: { readonly title: string; readonly meta?: string; readonly children: ReactNode }) {
  return (
    <details className="group rounded-nested border border-line bg-surface open:bg-panel-header">
      <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 text-[14px] font-medium text-primary [&::-webkit-details-marker]:hidden">
        <span className="flex flex-wrap items-center gap-2">
          {title}
          {meta ? <span className="font-mono text-[10.5px] font-normal tracking-[0.08em] text-meta">{meta}</span> : null}
        </span>
        <span aria-hidden="true" className="text-meta transition-transform group-open:rotate-45">
          +
        </span>
      </summary>
      <div className="border-t border-hairline px-4 py-3">{children}</div>
    </details>
  );
}

/** Whoever last wrote the section; otherwise the engine that drafted it or the party who must supply it. */
function authorFor(section: ReportSection, history: ReportDetail['history']): string {
  const written = history.find(
    (row) => row.event_type === 'section_updated' && row.detail?.section === section.key && row.detail?.action === 'edited',
  );
  if (written) return `${shortEmail(written.actor_email)}${written.actor_role && isRole(written.actor_role) ? ` · ${roleLabel[written.actor_role]}` : ''}`;
  if (section.mode === 'input') return copy.roleNames.input;
  if (section.lineage?.is_ai) return copy.roleNames.ai;
  return copy.roleNames.rules;
}

function Lifecycle({ detail }: { readonly detail: ReportDetail }) {
  const signed = detail.report.status === 'signed_off';
  const { progress } = detail;
  const steps = [
    { label: copy.stages.lock, detail: `${copy.dlp} ${formatDate(detail.report.data_lock_point)}`, state: 'locked' as const },
    {
      label: copy.stages.drafting,
      detail: copy.progress(progress.complete, progress.total),
      state: signed || detail.ready_for_signoff ? ('done' as const) : ('current' as const),
    },
    {
      label: copy.stages.review,
      detail: detail.ready_for_signoff || signed ? '✓' : '—',
      state: signed ? ('done' as const) : detail.ready_for_signoff ? ('current' as const) : ('pending' as const),
    },
    {
      label: copy.stages.signed,
      detail: detail.signoff ? formatDate(detail.signoff.signed_at) : '—',
      state: signed ? ('done' as const) : ('pending' as const),
    },
  ];
  return (
    <ol className="m-0 grid list-none grid-cols-2 gap-2 p-0 lg:grid-cols-4">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={cn(
            'flex min-w-0 items-center gap-3 rounded-nested border px-3 py-2.5',
            step.state === 'locked' && 'border-rose-line bg-rose-soft',
            step.state === 'done' && 'border-green-line bg-green-soft',
            step.state === 'current' && 'border-primary bg-surface',
            step.state === 'pending' && 'border-dashed border-strong bg-surface',
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              'flex size-7 shrink-0 items-center justify-center rounded-full font-mono text-[12px]',
              step.state === 'locked' && 'bg-rose text-on-ink',
              step.state === 'done' && 'bg-green-fill text-on-ink',
              step.state === 'current' && 'bg-ink text-on-ink',
              step.state === 'pending' && 'border border-strong text-meta',
            )}
          >
            {step.state === 'locked' ? <LockIcon size={14} /> : step.state === 'done' ? <StepCheckIcon size={14} /> : index + 1}
          </span>
          <span className="flex min-w-0 flex-col">
            <span className={cn('text-[13.5px] font-medium', step.state === 'locked' ? 'text-rose' : step.state === 'done' ? 'text-green' : 'text-primary')}>
              {step.label}
            </span>
            <span className="truncate font-mono text-[11px] text-meta">
              {step.state === 'locked' ? `${copy.locked} · ` : ''}
              {step.detail}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export default async function ReportPage({ params, searchParams }: PageProps<'/[tenant_slug]/dossier/[reportNumber]'>) {
  const { tenant_slug: slug, reportNumber: rawNumber } = await params;
  const reportNumber = decodeURIComponent(rawNumber);
  const query = await searchParams;
  const view = query.view === 'document' ? 'document' : 'workflow';
  const workspace = await getWorkspace();
  const result = await loadReport(reportNumber);
  const base = `/${slug}/dossier/`;
  const here = `${base}${encodeURIComponent(reportNumber)}/`;
  const crumbs = [
    { label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` },
    { label: dossierCopy.title, href: base },
    { label: reportNumber },
  ];

  if (!result.ok) {
    return (
      <>
        <PageHeader crumbs={crumbs} title={reportNumber} />
        <PageBody>
          <LoadFailed error={result.error} />
        </PageBody>
      </>
    );
  }

  const detail = result.data;
  const { report, content, progress } = detail;
  const sections = content.sections;
  const requested = typeof query.section === 'string' ? query.section : null;
  const section = sections.find((item) => item.key === requested) ?? sections.find((item) => !isDone(item.status)) ?? sections[0];
  const panel = query.panel === 'comments' ? 'comments' : 'provenance';
  const editing = query.edit === '1' && detail.permissions.edit;
  const sectionHref = (key: string, extra = '') => `${here}?section=${key}${extra}`;
  const signed = report.status === 'signed_off';
  const remaining = progress.draft + progress.input_required;

  return (
    <>
      <PageHeader
        crumbs={crumbs}
        title={
          <>
            <span className="font-mono text-[22px] tracking-[-0.01em] sm:text-[24px]">{reportNumber}</span>
          </>
        }
        meta={
          <>
            <Chip tone="muted" size="sm">
              {reportTypeLabel[report.report_type] ?? report.report_type}
            </Chip>
            <Chip tone={signed ? 'green' : 'default'} size="sm">
              {(reportStatusLabel[report.status] ?? report.status).toUpperCase()}
            </Chip>
            <span className="font-mono text-[12px] text-meta">
              {report.product_name} · {copy.interval} {formatDate(report.interval_start)} → {formatDate(report.data_lock_point)} · v
              {detail.version}
            </span>
          </>
        }
        actions={
          <ButtonLink href={`${here}export/`} variant="panel" download>
            <DownloadIcon size={16} />
            {copy.export}
          </ButtonLink>
        }
      >
        <Lifecycle detail={detail} />
        <SegmentedTabs
          label={copy.viewsLabel}
          items={copy.views.map((item) => ({
            label: item.label,
            href: item.value === 'workflow' ? here : `${here}?view=${item.value}`,
            active: item.value === view,
          }))}
        />
      </PageHeader>

      <PageBody>
        {view === 'document' ? (
          <article className="mx-auto flex w-full max-w-[860px] flex-col gap-8 rounded-panel border border-line bg-surface px-5 py-8 sm:px-10">
            <header className="flex flex-col gap-2 border-b border-hairline pb-6">
              <span className="font-mono text-[11px] tracking-[0.1em] text-meta uppercase">
                {reportTypeLabel[report.report_type]} · {content.product.name}
              </span>
              <h2 className="m-0 text-[24px] leading-[1.2] font-semibold tracking-[-0.02em] text-primary">
                {content.product.name} — {copy.interval} {formatDate(content.interval.start)} to {formatDate(content.interval.data_lock_point)}
              </h2>
              <span className="text-[13px] text-meta">
                {content.product.active_ingredient} · RSI {content.product.rsi_version ?? '—'}
              </span>
            </header>
            {sections.map((item) => (
              <section key={item.key} id={item.key} className="flex flex-col gap-3">
                <h3 className="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[18px] font-semibold tracking-[-0.01em] text-primary">
                  <span className="font-mono text-[14px] text-meta">{item.number}.</span>
                  {item.title}
                  <SectionStatusChip status={item.status} />
                </h3>
                {item.text ? <TraceableText text={item.text} tenantSlug={slug} /> : <p className="m-0 text-[14px] text-meta italic">{copy.empty}</p>}
                <SectionTables section={item} />
              </section>
            ))}
          </article>
        ) : (
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
            {/* Outline. Below xl this column dissolves so the order reads outline, section, provenance, data. */}
            <div className="contents xl:col-span-3 xl:flex xl:min-w-0 xl:flex-col xl:gap-5">
              <Panel title={copy.outline} bodyClassName="p-0" className="order-1 xl:order-none">
                <div className="flex flex-col gap-2 border-b border-hairline px-4 py-3 sm:px-5">
                  <span className="flex items-center justify-between text-[12.5px] text-meta">
                    {copy.progress(progress.complete, progress.total)}
                    <span className="font-mono">{Math.round((progress.complete / Math.max(1, progress.total)) * 100)}%</span>
                  </span>
                  <ProgressBar width={(progress.complete / Math.max(1, progress.total)) * 100} tone="green" />
                </div>
                <nav aria-label={copy.outline}>
                  <ol className="m-0 flex list-none flex-col p-1.5">
                    {sections.map((item) => {
                      const active = item.key === section?.key;
                      return (
                        <li key={item.key}>
                          <Link
                            href={sectionHref(item.key)}
                            aria-current={active ? 'true' : undefined}
                            className={cn(
                              'flex min-h-[40px] items-center gap-2.5 rounded-control px-2.5 py-1.5 text-[13.5px] leading-[1.3]',
                              active ? 'bg-ink text-on-ink' : 'text-secondary hover:bg-raised',
                            )}
                          >
                            <span className={cn('w-5 shrink-0 font-mono text-[11px]', active ? 'text-on-ink' : 'text-meta')}>{item.number}</span>
                            <span className="min-w-0 flex-1">{item.title}</span>
                            <span className={active ? 'text-on-ink [&_*]:text-on-ink' : ''}>
                              <StatusIcon status={item.status} />
                            </span>
                          </Link>
                        </li>
                      );
                    })}
                  </ol>
                </nav>
              </Panel>
              <Panel title={copy.dataPackage} className="order-4 xl:order-none">
                <dl className="m-0 grid grid-cols-2 gap-2">
                  {Object.entries(copy.stats).map(([key, label]) =>
                    key in content.data.stats ? (
                      <div key={key} className="flex flex-col gap-0.5 rounded-control border border-hairline bg-panel-header px-2.5 py-2">
                        <dt className="text-[11.5px] leading-[1.3] text-meta">{label}</dt>
                        <dd className="m-0 font-mono text-[16px] text-primary">{formatCount(content.data.stats[key])}</dd>
                      </div>
                    ) : null,
                  )}
                </dl>
              </Panel>
            </div>

            {/* Section */}
            {section ? (
              <div className="order-2 flex min-w-0 flex-col gap-4 xl:order-none xl:col-span-6">
                <section aria-labelledby="section-title" className="flex flex-col gap-5 rounded-card border border-line bg-surface p-4 sm:p-6">
                  <div className="flex flex-col gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <SectionStatusChip status={section.status} />
                      <Chip tone="muted" size="sm">
                        {copy.mode[section.mode] ?? section.mode.toUpperCase()}
                      </Chip>
                      {section.lineage?.model_id ? <EngineChip isAi={Boolean(section.lineage.is_ai)} /> : null}
                      {section.citations.length ? (
                        <Chip tone="green" size="sm">
                          {copy.cited(section.citations.length)}
                        </Chip>
                      ) : null}
                    </div>
                    <h2 id="section-title" className="m-0 flex items-baseline gap-3 text-[21px] leading-[1.25] font-semibold tracking-[-0.02em] text-primary">
                      <span className="font-mono text-[15px] text-meta">{section.number}.</span>
                      {section.title}
                    </h2>
                    <dl className="m-0 grid grid-cols-1 gap-2 rounded-nested border border-hairline bg-panel-header p-3 sm:grid-cols-3">
                      {[
                        { label: copy.roles.author, value: authorFor(section, detail.history) },
                        { label: copy.roles.reviewer, value: copy.roleNames.reviewer },
                        { label: copy.roles.approver, value: copy.roleNames.approver },
                      ].map((role) => (
                        <div key={role.label} className="flex flex-col gap-0.5">
                          <dt className="font-mono text-[10.5px] tracking-[0.08em] text-meta uppercase">{role.label}</dt>
                          <dd className="m-0 text-[13.5px] text-primary">{role.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>

                  {editing ? (
                    <SectionEditor
                      reportNumber={reportNumber}
                      sectionKey={section.key}
                      version={detail.version}
                      text={section.text ?? ''}
                      cancelHref={sectionHref(section.key)}
                    />
                  ) : (
                    <>
                      <div className="flex flex-col gap-3">
                        {section.text ? <TraceableText text={section.text} tenantSlug={slug} /> : <EmptyState>{copy.empty}</EmptyState>}
                      </div>
                      <SectionTables section={section} />
                      {section.warnings.length ? (
                        <div className="flex flex-col gap-1.5 rounded-nested border border-strong p-3">
                          <span className="flex items-center gap-2 text-[13px] font-medium text-primary">
                            <AlertIcon size={16} />
                            {copy.warnings}
                          </span>
                          <ul className="m-0 list-disc pl-5 text-[13.5px] text-secondary">
                            {section.warnings.map((warning) => (
                              <li key={warning}>{warning}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {detail.permissions.edit ? (
                        <div className="flex flex-wrap items-start gap-2 border-t border-hairline pt-4">
                          {section.status === 'draft' ? (
                            <AcceptSection reportNumber={reportNumber} sectionKey={section.key} version={detail.version} />
                          ) : null}
                          {section.mode !== 'generated' ? (
                            <ButtonLink href={sectionHref(section.key, '&edit=1')} variant="panel">
                              <PencilIcon size={16} />
                              {copy.edit}
                            </ButtonLink>
                          ) : null}
                        </div>
                      ) : null}
                    </>
                  )}

                  <div className="flex flex-col gap-2">
                    <Disclosure title={copy.guidance} meta={copy.guidanceSource(report.report_type)}>
                      <p className="m-0 text-[14px] leading-[1.6] text-secondary">{sectionGuidance[section.key] ?? '—'}</p>
                    </Disclosure>
                    <Disclosure title={copy.activity}>
                      <ActivityFeed
                        rows={detail.history.filter((row) => row.detail?.section === section.key)}
                        tenantSlug={slug}
                        empty={copy.noActivity}
                      />
                    </Disclosure>
                  </div>
                </section>
              </div>
            ) : null}

            {/* Provenance, comments, sign-off */}
            <aside aria-label={copy.provenance} className="order-3 flex min-w-0 flex-col gap-5 xl:order-none xl:col-span-3">
              <Panel bodyClassName="p-0">
                <div className="border-b border-hairline p-2">
                  <SegmentedTabs
                    label={copy.provenance}
                    className="[&_ul]:flex [&_ul]:w-full [&_li]:flex-1 [&_a]:justify-center"
                    items={[
                      { label: copy.provenance, href: sectionHref(section?.key ?? ''), active: panel === 'provenance' },
                      { label: copy.comments, href: sectionHref(section?.key ?? '', '&panel=comments'), active: panel === 'comments' },
                    ]}
                  />
                </div>
                <div className="p-4">
                  {panel === 'provenance' && section ? (
                    <div className="flex flex-col gap-4">
                      {section.lineage?.model_id ? (
                        <KeyValues
                          columns={1}
                          items={[
                            { label: copy.lineage.task, value: <span className="font-mono text-[13px]">{section.lineage.task ?? '—'}</span> },
                            { label: copy.lineage.engine, value: <EngineChip isAi={Boolean(section.lineage.is_ai)} /> },
                            { label: copy.lineage.model, value: <span className="font-mono text-[13px]">{section.lineage.model_id}</span> },
                          ]}
                        />
                      ) : (
                        <p className="m-0 text-[13.5px] leading-[1.5] text-muted">
                          {!section.text?.trim()
                            ? copy.lineage.awaiting
                            : section.status === 'edited' || section.mode === 'input'
                              ? copy.lineage.human
                              : copy.lineage.assembled}
                        </p>
                      )}
                      <KeyValues
                        columns={1}
                        items={[
                          { label: copy.lineage.rules, value: <span className="font-mono text-[13px]">{content.rules_version}</span> },
                          { label: copy.lineage.generated, value: formatDateTime(content.generated_at) },
                          { label: copy.lineage.version, value: `v${detail.version}` },
                        ]}
                      />
                      <div className="flex flex-col gap-1.5">
                        <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.lineage.citations}</span>
                        {section.citations.length ? (
                          <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
                            {section.citations.map((citation) => (
                              <li key={citation}>
                                <Link
                                  href={`/${slug}/verify/${citation}/`}
                                  className="inline-flex min-h-[28px] items-center rounded-chip border border-green-line bg-green-soft px-2 font-mono text-[11.5px] text-green hover:underline"
                                >
                                  {citation}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="m-0 text-[13px] text-meta">{copy.lineage.noCitations}</p>
                        )}
                      </div>
                    </div>
                  ) : null}
                  {panel === 'comments' && section ? (
                    workspace.sample ? (
                      <div className="flex flex-col gap-3">
                        {(sampleComments[`${reportNumber}/${section.key}`] ?? []).map((comment, index) => (
                          <article key={index} className="flex flex-col gap-1 rounded-nested border border-hairline bg-panel-header p-3">
                            <span className="flex flex-wrap items-center gap-x-2 text-[12.5px]">
                              <span className="font-medium text-primary">{shortEmail(comment.author)}</span>
                              <span className="text-meta">{comment.role}</span>
                            </span>
                            <p className="m-0 text-[13.5px] leading-[1.5] text-secondary">{comment.body}</p>
                          </article>
                        ))}
                        <p className="m-0 font-mono text-[11px] leading-[1.5] text-meta">{copy.commentsSample}</p>
                      </div>
                    ) : (
                      <p className="m-0 text-[13.5px] leading-[1.5] text-muted">{copy.commentsLive}</p>
                    )
                  ) : null}
                </div>
              </Panel>

              <Panel title={copy.signoff.heading}>
                {detail.signoff ? (
                  <div className="flex flex-col gap-2 rounded-nested border border-green-line bg-green-soft p-3">
                    <Chip tone="green" size="xs" className="w-fit">
                      {copy.signoff.signed.toUpperCase()}
                    </Chip>
                    <p className="m-0 text-[13.5px] leading-[1.5] text-secondary">“{detail.signoff.meaning}”</p>
                    <span className="text-[12.5px] text-meta">
                      {copy.signoff.by} {shortEmail(detail.signoff.signer_email)} · {formatDateTime(detail.signoff.signed_at)} · v{detail.signoff.version}
                    </span>
                    <p className="m-0 text-[12.5px] text-meta">{copy.signoff.locked}</p>
                  </div>
                ) : detail.permissions.signoff ? (
                  detail.ready_for_signoff ? (
                    <div className="flex flex-col gap-3">
                      <p className="m-0 text-[13.5px] text-secondary">{copy.signoff.ready}</p>
                      <SignOffForm reportNumber={reportNumber} version={detail.version} meaning={detail.signoff_meaning} />
                    </div>
                  ) : (
                    <p className="m-0 text-[13.5px] leading-[1.5] text-muted">{copy.signoff.notReady(remaining)}</p>
                  )
                ) : (
                  <p className="m-0 text-[13.5px] leading-[1.5] text-muted">
                    {remaining ? copy.signoff.notReady(remaining) : copy.signoff.ready} {copy.signoff.notQppv}
                  </p>
                )}
              </Panel>
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}
