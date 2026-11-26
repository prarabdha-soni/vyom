import type { Metadata } from 'next';
import Link from 'next/link';
import { dossierCopy, reportStatusLabel, reportTypeLabel } from '@/content/console';
import { CreateReportForm } from '@/components/console/dossier/DossierControls';
import { EmptyState, LoadFailed, PageBody, PageHeader, Panel, td, th } from '@/components/console/ui';
import { PlusIcon } from '@/components/icons';
import { ButtonLink, Chip, ProgressBar, ScrollableTable } from '@/components/ui';
import { can, getWorkspace, loadProducts, loadReport, loadReports } from '@/lib/console/data';
import { formatDate, formatDateTime, shortEmail } from '@/lib/console/format';

export const metadata: Metadata = { title: dossierCopy.title };

export default async function DossierPage({ params, searchParams }: PageProps<'/[tenant_slug]/dossier'>) {
  const { tenant_slug: slug } = await params;
  const query = await searchParams;
  const workspace = await getWorkspace();
  const canCreate = can(workspace, 'report.create');
  const creating = query.new === '1' && canCreate;
  const [reports, products] = await Promise.all([loadReports(), creating ? loadProducts() : Promise.resolve(null)]);
  const base = `/${slug}/dossier/`;

  // Progress lives on each report; fetch it for the first page of reports.
  const progress = new Map(
    reports.ok
      ? (await Promise.all(reports.data.slice(0, 20).map((report) => loadReport(report.report_number)))).flatMap((loaded) =>
          loaded.ok ? [[loaded.data.report.report_number, loaded.data.progress] as const] : [],
        )
      : [],
  );

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` }, { label: dossierCopy.title }]}
        title={dossierCopy.title}
        lead={dossierCopy.lead}
        actions={
          canCreate && !creating ? (
            <ButtonLink href={`${base}?new=1`} variant="panelPrimary">
              <PlusIcon size={16} />
              {dossierCopy.create.open}
            </ButtonLink>
          ) : null
        }
      />
      <PageBody>
        {creating && products?.ok ? (
          <Panel title={dossierCopy.create.heading} action={{ label: dossierCopy.workspace.cancel, href: base }}>
            <CreateReportForm products={products.data.map((p) => ({ code: p.code, name: p.name }))} today={workspace.today} />
          </Panel>
        ) : null}

        {!reports.ok ? (
          <LoadFailed error={reports.error} />
        ) : reports.data.length === 0 ? (
          <EmptyState>{dossierCopy.empty}</EmptyState>
        ) : (
          <Panel bodyClassName="p-0">
            <ScrollableTable label={dossierCopy.title}>
              <table className="w-full min-w-[860px] border-collapse">
                <thead>
                  <tr>
                    {dossierCopy.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reports.data.map((report) => {
                    const done = progress.get(report.report_number);
                    return (
                      <tr key={report.report_number} className="hover:bg-panel-header">
                        <td className={td}>
                          <Link href={`${base}${report.report_number}/`} className="flex flex-col items-start gap-1">
                            <span className="font-mono text-[13px] font-medium text-primary hover:underline">{report.report_number}</span>
                            <Chip tone="muted" size="xs">
                              {reportTypeLabel[report.report_type] ?? report.report_type}
                            </Chip>
                          </Link>
                        </td>
                        <td className={`${td} text-primary`}>{report.product_code}</td>
                        <td className={`${td} font-mono text-[12.5px] whitespace-nowrap`}>
                          {formatDate(report.interval_start)} → {formatDate(report.data_lock_point)}
                        </td>
                        <td className={`${td} w-[220px]`}>
                          {done ? (
                            <span className="flex items-center gap-3">
                              <ProgressBar width={(done.complete / Math.max(1, done.total)) * 100} tone="green" />
                              <span className="shrink-0 font-mono text-[11.5px] text-meta">
                                {done.complete}/{done.total}
                              </span>
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className={td}>
                          <span className="flex flex-col items-start gap-1">
                            <Chip tone={report.status === 'signed_off' ? 'green' : 'default'} size="xs">
                              {(reportStatusLabel[report.status] ?? report.status).toUpperCase()}
                            </Chip>
                            {report.signed_at ? (
                              <span className="text-[12px] text-meta">
                                {shortEmail(report.signed_by_email)} · {formatDateTime(report.signed_at)}
                              </span>
                            ) : null}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </ScrollableTable>
          </Panel>
        )}
      </PageBody>
    </>
  );
}
