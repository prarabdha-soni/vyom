import type { Metadata } from 'next';
import { opsCopy } from '@/content/console';
import { LoadFailed, PageBody, PageHeader, Panel, td, th } from '@/components/console/ui';
import { Chip, ScrollableTable } from '@/components/ui';
import { loadOps } from '@/lib/console/data';
import { formatCount, formatDateTime } from '@/lib/console/format';

export const metadata: Metadata = { title: opsCopy.title };

export default async function OpsPage() {
  const result = await loadOps();
  return (
    <>
      <PageHeader
        title={opsCopy.title}
        lead={opsCopy.lead}
        meta={
          result.ok ? (
            <>
              <Chip tone="muted" size="sm">
                {opsCopy.scope}: {result.data.scope.toUpperCase()}
              </Chip>
              <Chip tone="muted" size="sm">
                {opsCopy.aiMode}: {result.data.ai_mode.toUpperCase()}
              </Chip>
            </>
          ) : null
        }
      />
      <PageBody>
        {result.ok ? (
          <Panel bodyClassName="p-0">
            <ScrollableTable label={opsCopy.title}>
              <table className="w-full min-w-[720px] border-collapse">
                <thead>
                  <tr>
                    {opsCopy.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.data.tenants.map((tenant) => (
                    <tr key={tenant.slug}>
                      <td className={td}>
                        <span className="flex flex-col gap-0.5">
                          <span className="font-medium text-primary">{tenant.display_name}</span>
                          <span className="font-mono text-[12px] text-meta">/{tenant.slug}</span>
                        </span>
                      </td>
                      <td className={td}>{tenant.last_sweep ? formatDateTime(tenant.last_sweep) : opsCopy.never}</td>
                      <td className={`${td} font-mono`}>{formatCount(tenant.model_calls_7d)}</td>
                      <td className={`${td} font-mono ${tenant.model_failures_7d ? 'text-rose' : ''}`}>
                        {formatCount(tenant.model_failures_7d)}
                      </td>
                      <td className={`${td} font-mono`}>{formatCount(tenant.open_cases)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollableTable>
          </Panel>
        ) : (
          <LoadFailed error={result.error} />
        )}
      </PageBody>
    </>
  );
}
