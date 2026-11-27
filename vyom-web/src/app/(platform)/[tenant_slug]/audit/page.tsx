import type { Metadata } from 'next';
import Link from 'next/link';
import { auditCopy, eventVerb } from '@/content/console';
import { EmptyState, LoadFailed, PageBody, PageHeader, Panel, SegmentedTabs, entityHref, entityLabel, td, th } from '@/components/console/ui';
import { ScrollableTable } from '@/components/ui';
import { roleLabel, isRole } from '@/lib/auth/roles';
import { getWorkspace, loadAudit } from '@/lib/console/data';
import { formatDateTime } from '@/lib/console/format';

export const metadata: Metadata = { title: auditCopy.title };

const KINDS = new Set<string>(auditCopy.filters.map((filter) => filter.value));

export default async function AuditPage({ params, searchParams }: PageProps<'/[tenant_slug]/audit'>) {
  const { tenant_slug: slug } = await params;
  const query = await searchParams;
  const kind = typeof query.kind === 'string' && KINDS.has(query.kind) ? query.kind : '';
  const workspace = await getWorkspace();
  const result = await loadAudit();
  const base = `/${slug}/audit/`;
  const rows = result.ok ? result.data.filter((row) => !kind || row.entity_kind === kind) : [];

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` }, { label: auditCopy.title }]}
        title={auditCopy.title}
        lead={auditCopy.lead}
      >
        <SegmentedTabs
          label={auditCopy.title}
          items={auditCopy.filters.map((filter) => ({
            label: filter.label,
            href: filter.value ? `${base}?kind=${filter.value}` : base,
            active: filter.value === kind,
          }))}
        />
      </PageHeader>
      <PageBody>
        {!result.ok ? (
          <LoadFailed error={result.error} />
        ) : rows.length === 0 ? (
          <EmptyState>{auditCopy.empty}</EmptyState>
        ) : (
          <Panel bodyClassName="p-0">
            <ScrollableTable label={auditCopy.title}>
              <table className="w-full min-w-[760px] border-collapse">
                <thead>
                  <tr>
                    {auditCopy.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => {
                    const href = entityHref(slug, row.entity_kind, row.entity_ref);
                    const label = entityLabel(row.entity_kind, row.entity_ref) ?? row.entity_kind;
                    return (
                      <tr key={`${row.created_at}-${index}`}>
                        <td className={`${td} font-mono text-[12px] whitespace-nowrap text-meta`}>{formatDateTime(row.created_at)}</td>
                        <td className={td}>
                          <span className="flex flex-col gap-0.5">
                            <span className="text-primary">{row.actor_email ?? 'Vyom'}</span>
                            {row.actor_role ? (
                              <span className="text-[12px] text-meta">{isRole(row.actor_role) ? roleLabel[row.actor_role] : row.actor_role}</span>
                            ) : null}
                          </span>
                        </td>
                        <td className={td}>{eventVerb[row.event_type] ?? row.event_type.replace(/_/g, ' ')}</td>
                        <td className={td}>
                          {href ? (
                            <Link href={href} className="font-mono text-[12.5px] text-primary hover:underline">
                              {label}
                            </Link>
                          ) : (
                            <span className="font-mono text-[12.5px]">{label}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </ScrollableTable>
            <p className="m-0 border-t border-hairline px-4 py-3 text-[12.5px] text-meta sm:px-5">{auditCopy.limit}</p>
          </Panel>
        )}
      </PageBody>
    </>
  );
}
