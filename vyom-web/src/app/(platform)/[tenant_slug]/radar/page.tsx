import type { Metadata } from 'next';
import Link from 'next/link';
import { radarCopy } from '@/content/console';
import { SweepButton } from '@/components/console/radar/RadarClient';
import {
  BandChip,
  EmptyState,
  LoadFailed,
  OutcomeChip,
  PageBody,
  PageHeader,
  Panel,
  SegmentedTabs,
  td,
  th,
} from '@/components/console/ui';
import { Chip, ScrollableTable } from '@/components/ui';
import { type LiteratureView, can, getWorkspace, loadLiterature, loadProducts } from '@/lib/console/data';
import { formatDate, formatPercent } from '@/lib/console/format';

export const metadata: Metadata = { title: radarCopy.title };

const VIEWS: readonly LiteratureView[] = ['open', 'decided', 'all'];

export default async function RadarPage({ params, searchParams }: PageProps<'/[tenant_slug]/radar'>) {
  const { tenant_slug: slug } = await params;
  const query = await searchParams;
  const view = VIEWS.find((value) => value === query.view) ?? 'open';
  const product = typeof query.product === 'string' && query.product ? query.product : undefined;
  const workspace = await getWorkspace();
  const [queue, products] = await Promise.all([loadLiterature(view, product), loadProducts()]);
  const base = `/${slug}/radar/`;
  const counts = queue.ok ? queue.data.counts : {};
  const withProduct = (value: string) => `${base}?view=${value}${product ? `&product=${encodeURIComponent(product)}` : ''}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` }, { label: radarCopy.title }]}
        title={radarCopy.title}
        lead={radarCopy.lead}
        actions={can(workspace, 'literature.screen') ? <SweepButton /> : null}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SegmentedTabs
            label={radarCopy.title}
            items={radarCopy.views.map((item) => ({
              label: item.label,
              href: withProduct(item.value),
              active: item.value === view,
              count: item.value === 'open' ? counts.open : item.value === 'decided' ? counts.decided : undefined,
            }))}
          />
          {products.ok ? (
            <form method="get" action={base} className="flex items-center gap-2">
              <input type="hidden" name="view" value={view} />
              <label className="flex items-center gap-2 text-[13px] text-secondary">
                {radarCopy.product.label}
                <select
                  name="product"
                  defaultValue={product ?? ''}
                  className="min-h-[36px] rounded-control border border-button bg-surface px-2.5 text-[13.5px] text-primary"
                >
                  <option value="">{radarCopy.product.all}</option>
                  {products.data.map((item) => (
                    <option key={item.code} value={item.code}>
                      {item.code}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="min-h-[36px] cursor-pointer rounded-control border border-button bg-surface px-3 text-[13px] font-medium text-primary hover:bg-raised"
              >
                {radarCopy.product.apply}
              </button>
            </form>
          ) : null}
        </div>
      </PageHeader>
      <PageBody>
        {!queue.ok ? (
          <LoadFailed error={queue.error} />
        ) : queue.data.items.length === 0 ? (
          <EmptyState>{view === 'open' && !product ? radarCopy.empty.open : radarCopy.empty.other}</EmptyState>
        ) : (
          <Panel bodyClassName="p-0">
            <ScrollableTable label={radarCopy.title}>
              <table className="w-full min-w-[880px] border-collapse">
                <thead>
                  <tr>
                    {radarCopy.columns.map((column) => (
                      <th key={column} scope="col" className={th}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {queue.data.items.map((item) => (
                    <tr key={item.state_id} className="hover:bg-panel-header">
                      <td className={`${td} w-[48%]`}>
                        <Link href={`${base}${item.state_id}/`} className="group flex flex-col gap-1">
                          <span className="font-mono text-[12px] text-meta">{item.reference}</span>
                          <span className="text-[14.5px] leading-[1.4] font-medium text-primary group-hover:underline">{item.title}</span>
                          <span className="text-[12.5px] text-meta">
                            {item.journal ?? '—'} · {formatDate(item.pub_date)}
                          </span>
                        </Link>
                      </td>
                      <td className={td}>
                        <span className="flex flex-wrap gap-1">
                          {item.products.map((code) => (
                            <Chip key={code} tone="muted" size="xs">
                              {code}
                            </Chip>
                          ))}
                        </span>
                      </td>
                      <td className={td}>
                        <BandChip band={item.band} />
                      </td>
                      <td className={`${td} whitespace-nowrap`}>
                        <span className="flex flex-col gap-0.5">
                          <span className="text-primary">{item.criteria_met === null ? '—' : radarCopy.criteriaMet(item.criteria_met)}</span>
                          <span className="font-mono text-[11.5px] text-meta">P(serious) {formatPercent(item.p_serious)}</span>
                        </span>
                      </td>
                      <td className={td}>
                        {item.outcome ? (
                          <span className="flex flex-col items-start gap-1">
                            <OutcomeChip outcome={item.outcome} />
                            {item.case_number ? (
                              <Link href={`/${slug}/verify/${item.case_number}/`} className="font-mono text-[12px] text-primary hover:underline">
                                {item.case_number}
                              </Link>
                            ) : null}
                          </span>
                        ) : (
                          <span className="text-[13px] text-meta">{radarCopy.pending}</span>
                        )}
                      </td>
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
