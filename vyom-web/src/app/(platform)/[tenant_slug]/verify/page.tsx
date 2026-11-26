import type { Metadata } from 'next';
import Link from 'next/link';
import { channelLabel, verifyCopy } from '@/content/console';
import { PlusIcon } from '@/components/icons';
import {
  CaseStatusChip,
  ClockChip,
  EmptyState,
  LoadFailed,
  PageBody,
  PageHeader,
  Panel,
  SegmentedTabs,
  td,
  th,
} from '@/components/console/ui';
import { ButtonLink, Chip, ScrollableTable } from '@/components/ui';
import { can, getWorkspace, loadCases } from '@/lib/console/data';
import { formatDate, formatDateTime } from '@/lib/console/format';

export const metadata: Metadata = { title: verifyCopy.title };

const STATUSES = new Set(['open', '', 'data_entry', 'medical_review', 'approved', 'closed_invalid', 'duplicate']);

export default async function VerifyPage({ params, searchParams }: PageProps<'/[tenant_slug]/verify'>) {
  const { tenant_slug: slug } = await params;
  const query = await searchParams;
  const requested = typeof query.status === 'string' ? query.status : 'open';
  const status = STATUSES.has(requested) ? requested : 'open';
  const workspace = await getWorkspace();
  const result = await loadCases(status || undefined);
  const base = `/${slug}/verify/`;
  const counts = result.ok ? result.data.counts : {};
  const countFor = (value: string) =>
    value === 'open'
      ? (counts.data_entry ?? 0) + (counts.medical_review ?? 0)
      : value
        ? (counts[value] ?? 0)
        : Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` }, { label: verifyCopy.title }]}
        title={verifyCopy.title}
        lead={verifyCopy.lead}
        actions={
          can(workspace, 'case.create') ? (
            <ButtonLink href={`${base}new/`} variant="panelPrimary">
              <PlusIcon size={16} />
              {verifyCopy.newCase}
            </ButtonLink>
          ) : null
        }
      >
        <SegmentedTabs
          label={verifyCopy.title}
          items={verifyCopy.views.map((view) => ({
            label: view.label,
            href: `${base}?status=${view.value}`,
            active: view.value === status,
            count: countFor(view.value),
          }))}
        />
      </PageHeader>
      <PageBody>
        {!result.ok ? (
          <LoadFailed error={result.error} />
        ) : result.data.items.length === 0 ? (
          <EmptyState>{verifyCopy.empty}</EmptyState>
        ) : (
          <Panel bodyClassName="p-0">
            <ScrollableTable label={verifyCopy.title}>
              <table className="w-full min-w-[920px] border-collapse">
                <thead>
                  <tr>
                    {verifyCopy.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.data.items.map((item) => (
                    <tr key={item.case_number} className="hover:bg-panel-header">
                      <td className={td}>
                        <Link href={`${base}${item.case_number}/`} className="flex flex-col gap-0.5">
                          <span className="font-mono text-[13px] font-medium text-primary hover:underline">{item.case_number}</span>
                          <span className="text-[12.5px] text-meta">{channelLabel[item.source_channel] ?? item.source_channel}</span>
                        </Link>
                      </td>
                      <td className={td}>
                        <span className="flex flex-col gap-0.5">
                          <span className="text-primary">{item.product_code ?? '—'}</span>
                          <span className="text-[13px]">
                            {item.first_event ?? '—'}
                            {item.event_count > 1 ? <span className="text-meta"> +{item.event_count - 1}</span> : null}
                          </span>
                        </span>
                      </td>
                      <td className={td}>
                        <span className="flex flex-wrap gap-1">
                          {item.serious ? (
                            <Chip tone="default" size="xs">
                              {verifyCopy.serious}
                            </Chip>
                          ) : (
                            <span className="text-[13px] text-meta">{verifyCopy.nonSerious}</span>
                          )}
                          {item.expedited_candidate ? (
                            <Chip tone="default" size="xs">
                              {verifyCopy.expedited}
                            </Chip>
                          ) : null}
                        </span>
                      </td>
                      <td className={td}>
                        <CaseStatusChip status={item.status} />
                      </td>
                      <td className={td}>
                        <span className="flex flex-col items-start gap-1">
                          <ClockChip clock={item.clock} />
                          {item.clock.due_date && item.clock.status !== 'stopped' ? (
                            <span className="font-mono text-[11.5px] text-meta">{formatDate(item.clock.due_date)}</span>
                          ) : null}
                        </span>
                      </td>
                      <td className={`${td} font-mono text-[12px] whitespace-nowrap text-meta`}>{formatDateTime(item.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollableTable>
          </Panel>
        )}
      </PageBody>
    </>
  );
}
