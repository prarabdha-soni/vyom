import type { Metadata } from 'next';
import Link from 'next/link';
import { aiTaskLabel, dashboardCopy, pipelineStages, reportTypeLabel } from '@/content/console';
import {
  ActivityFeed,
  BandChip,
  ClockChip,
  EmptyState,
  EngineChip,
  Kpi,
  LoadFailed,
  PageBody,
  PageHeader,
  Panel,
} from '@/components/console/ui';
import { Chip, ProgressBar } from '@/components/ui';
import { cn } from '@/lib/cn';
import { getWorkspace, loadDashboard, loadReport } from '@/lib/console/data';
import { formatCount, formatDate, formatLongDate } from '@/lib/console/format';
import { AI_TASKS, type Dashboard } from '@/lib/gateway/types';

export const metadata: Metadata = { title: dashboardCopy.title };

export default async function DashboardPage({ params }: PageProps<'/[tenant_slug]/dashboard'>) {
  const { tenant_slug: slug } = await params;
  const workspace = await getWorkspace();
  const result = await loadDashboard();
  const base = `/${slug}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name }, { label: dashboardCopy.title }]}
        title={dashboardCopy.title}
        lead={`${formatLongDate(workspace.today)} · ${dashboardCopy.lead}`}
      />
      <PageBody>
        {result.ok ? <DashboardBody data={result.data} base={base} aiEnabled={workspace.me.ai.is_ai} routing={workspace.me.ai} /> : <LoadFailed error={result.error} />}
      </PageBody>
    </>
  );
}

async function DashboardBody({
  data,
  base,
  aiEnabled,
  routing,
}: {
  readonly data: Dashboard;
  readonly base: string;
  readonly aiEnabled: boolean;
  readonly routing: Awaited<ReturnType<typeof getWorkspace>>['me']['ai'];
}) {
  const { literature, cases, reports } = data;
  const copy = dashboardCopy;
  const drafts = reports.recent.filter((report) => report.status === 'draft').slice(0, 3);
  const progress = new Map(
    (await Promise.all(drafts.map((report) => loadReport(report.report_number)))).flatMap((loaded) =>
      loaded.ok ? [[loaded.data.report.report_number, loaded.data.progress] as const] : [],
    ),
  );
  const bands = [
    { key: 'RED', label: 'Red', count: literature.counts.open_red ?? 0, fill: 'bg-primary' },
    { key: 'YELLOW', label: 'Yellow', count: literature.counts.open_yellow ?? 0, fill: 'bg-dash' },
    { key: 'GREEN', label: 'Green', count: literature.counts.open_green ?? 0, fill: 'bg-strong' },
  ];
  const openTotal = Math.max(1, bands.reduce((sum, band) => sum + band.count, 0));
  const stageMax = Math.max(1, ...pipelineStages.map((stage) => cases.counts[stage.status] ?? 0));

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label={copy.kpis.literature.label}
          value={formatCount(literature.counts.open)}
          detail={copy.kpis.literature.detail(literature.counts.open_red ?? 0)}
          href={`${base}/radar/`}
        />
        <Kpi
          label={copy.kpis.cases.label}
          value={formatCount(cases.open)}
          detail={copy.kpis.cases.detail(cases.serious_open)}
          href={`${base}/verify/`}
        />
        <Kpi
          label={copy.kpis.expedited.label}
          value={formatCount(cases.expedited_candidates)}
          detail={copy.kpis.expedited.detail}
          href={`${base}/verify/`}
        />
        <Kpi
          label={copy.kpis.reports.label}
          value={formatCount(reports.draft)}
          detail={copy.kpis.reports.detail(reports.signed_off)}
          href={`${base}/dossier/`}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <Panel title={copy.literature.heading} action={{ label: copy.literature.link, href: `${base}/radar/` }} className="xl:col-span-7">
          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-2.5">
              <span className="text-[13px] text-meta">{copy.literature.bands}</span>
              <div aria-hidden="true" className="flex h-3 w-full overflow-hidden rounded-full bg-hairline">
                {bands.map((band) =>
                  band.count ? <div key={band.key} className={band.fill} style={{ width: `${(band.count / openTotal) * 100}%` }} /> : null,
                )}
              </div>
              <ul className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1 p-0 text-[13px] text-secondary">
                {bands.map((band) => (
                  <li key={band.key} className="flex items-center gap-1.5">
                    <span aria-hidden="true" className={cn('size-2.5 rounded-full', band.fill)} />
                    {band.label} <span className="font-mono text-primary">{band.count}</span>
                  </li>
                ))}
                <li className="text-meta">
                  {copy.literature.escalated} <span className="font-mono text-primary">{literature.counts.escalated ?? 0}</span>
                </li>
                <li className="text-meta">
                  {copy.literature.decided} <span className="font-mono text-primary">{literature.counts.decided ?? 0}</span>
                </li>
              </ul>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[13px] text-meta">{copy.literature.top}</span>
              <ul className="m-0 flex list-none flex-col p-0">
                {literature.top.slice(0, 4).map((item) => (
                  <li key={item.state_id} className="border-b border-hairline last:border-b-0">
                    <Link
                      href={`${base}/radar/${item.state_id}/`}
                      className="flex flex-wrap items-center gap-x-3 gap-y-1.5 py-2.5 hover:bg-panel-header sm:flex-nowrap"
                    >
                      <span className="w-[96px] shrink-0 font-mono text-[12px] text-meta">{item.reference}</span>
                      <span className="min-w-0 flex-[1_1_220px] text-[14px] leading-[1.4] text-primary">{item.title}</span>
                      <BandChip band={item.band} />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>

        <Panel title={copy.clock.heading} lead={copy.clock.lead} className="xl:col-span-5">
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: copy.clock.overdue, value: cases.clock.overdue, alert: cases.clock.overdue > 0 },
                { label: copy.clock.dueSoon, value: cases.clock.due_soon, alert: false },
                { label: copy.clock.onTrack, value: cases.clock.on_track, alert: false },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className={cn(
                    'flex flex-col gap-1 rounded-nested border px-3 py-2.5',
                    stat.alert ? 'border-rose-line bg-rose-soft' : 'border-hairline bg-panel-header',
                  )}
                >
                  <span className={cn('text-[22px] leading-none font-semibold tabular-nums', stat.alert ? 'text-rose' : 'text-primary')}>
                    {stat.value}
                  </span>
                  <span className="text-[12px] text-meta">{stat.label}</span>
                </div>
              ))}
            </div>
            {cases.next_due.length ? (
              <ul className="m-0 flex list-none flex-col p-0">
                {cases.next_due.slice(0, 5).map((item) => (
                  <li key={item.case_number} className="border-b border-hairline last:border-b-0">
                    <Link href={`${base}/verify/${item.case_number}/`} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 hover:bg-panel-header">
                      <span className="font-mono text-[12.5px] text-primary">{item.case_number}</span>
                      <span className="min-w-0 flex-1 truncate text-[13.5px] text-secondary">
                        {item.product_code} · {item.first_event ?? '—'}
                      </span>
                      <ClockChip clock={item.clock} />
                      <span className="w-full font-mono text-[11.5px] text-meta sm:w-auto">{formatDate(item.clock.due_date)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState>{copy.clock.empty}</EmptyState>
            )}
          </div>
        </Panel>

        <Panel title={copy.pipeline.heading} action={{ label: copy.pipeline.link, href: `${base}/verify/` }} className="xl:col-span-7">
          <ol className="m-0 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-5">
            {pipelineStages.map((stage) => {
              const count = cases.counts[stage.status] ?? 0;
              return (
                <li key={stage.status}>
                  <Link
                    href={`${base}/verify/?status=${stage.status}`}
                    className="flex h-full flex-col gap-2.5 rounded-nested border border-hairline bg-panel-header p-3 hover:border-strong"
                  >
                    <span className="text-[12.5px] leading-[1.3] text-meta">{stage.label}</span>
                    <span className="text-[24px] leading-none font-semibold text-primary tabular-nums">{count}</span>
                    <ProgressBar width={(count / stageMax) * 100} tone={stage.status === 'approved' ? 'green' : 'ink'} />
                  </Link>
                </li>
              );
            })}
          </ol>
        </Panel>

        <Panel title={copy.reports.heading} action={{ label: copy.reports.link, href: `${base}/dossier/` }} className="xl:col-span-5">
          {reports.recent.length ? (
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {reports.recent.slice(0, 4).map((report) => {
                const done = progress.get(report.report_number);
                return (
                  <li key={report.report_number}>
                    <Link
                      href={`${base}/dossier/${report.report_number}/`}
                      className="flex flex-col gap-2 rounded-nested border border-hairline p-3 hover:border-strong"
                    >
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[12.5px] text-primary">{report.report_number}</span>
                        <Chip tone="muted" size="xs">
                          {reportTypeLabel[report.report_type] ?? report.report_type}
                        </Chip>
                        <span className="text-[13px] text-secondary">{report.product_code}</span>
                        <span className="ml-auto">
                          {report.status === 'signed_off' ? (
                            <Chip tone="green" size="xs">
                              SIGNED OFF
                            </Chip>
                          ) : (
                            <Chip tone="default" size="xs">
                              DRAFT
                            </Chip>
                          )}
                        </span>
                      </span>
                      <span className="font-mono text-[11.5px] text-meta">
                        {formatDate(report.interval_start)} → {formatDate(report.data_lock_point)}
                      </span>
                      {done ? (
                        <span className="flex items-center gap-3">
                          <ProgressBar width={(done.complete / Math.max(1, done.total)) * 100} tone="green" />
                          <span className="shrink-0 font-mono text-[11.5px] text-meta">
                            {done.complete}/{done.total}
                          </span>
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState>{copy.reports.empty}</EmptyState>
          )}
        </Panel>

        <Panel title={copy.activity.heading} action={{ label: copy.activity.link, href: `${base}/audit/` }} className="xl:col-span-7">
          <ActivityFeed rows={data.activity} tenantSlug={base.slice(1)} empty={copy.activity.empty} />
        </Panel>

        <Panel title={copy.models.heading} lead={copy.models.lead} className="xl:col-span-5">
          <ul className="m-0 flex list-none flex-col p-0">
            {AI_TASKS.map((task) => {
              const route = routing[task];
              if (!route) return null;
              return (
                <li key={task} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-hairline py-2.5 last:border-b-0">
                  <span className="min-w-0 flex-1 text-[13.5px] text-primary">{aiTaskLabel[task]}</span>
                  <EngineChip isAi={aiEnabled && route.provider !== 'demo'} model={route.model_id} />
                </li>
              );
            })}
          </ul>
          <p className="m-0 mt-3 font-mono text-[11.5px] leading-[1.6] text-meta">
            {data.model_calls.length
              ? data.model_calls
                  .map((row) => `${copy.models.kind[row.call_kind] ?? row.call_kind.replace(/_/g, ' ')}: ${row.calls} ${copy.models.calls}, ${row.failed} ${copy.models.failed}`)
                  .join(' · ')
              : copy.models.empty}
          </p>
        </Panel>
      </div>
    </>
  );
}
