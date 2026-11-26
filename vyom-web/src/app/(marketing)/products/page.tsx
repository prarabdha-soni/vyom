import type { Metadata } from 'next';
import Link from 'next/link';
import { productsIndex } from '@/content/productPage';
import { capabilityMatrix, products, statusLabel } from '@/content/products';
import { ArrowRightIcon, CheckIcon, productIcons } from '@/components/icons';
import { Chip, Eyebrow, ScrollableTable, Section } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Modules',
  description:
    'Three modules on one safety system: Vyom Radar for intake and literature screening, Vyom Verify for case processing and quality checks, and Vyom Dossier for periodic reports.',
};

export default function ProductsPage() {
  return (
    <>
      <Section>
        <div className="flex flex-col gap-14">
          <div data-reveal className="flex max-w-[760px] flex-col gap-4">
            <Eyebrow>{productsIndex.eyebrow}</Eyebrow>
            <h1 className="m-0 text-[clamp(36px,4.4vw,60px)] leading-[1.04] font-semibold tracking-[-0.03em] text-balance text-primary">
              {productsIndex.heading}
            </h1>
            <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">
              {productsIndex.lead}
            </p>
          </div>

          <ul
            data-reveal
            className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))] gap-4 p-0"
          >
            {products.map((product) => {
              const Icon = productIcons[product.slug];
              const roadmap = product.status === 'roadmap';
              return (
                <li key={product.slug} className="flex">
                  <Link
                    href={`/products/${product.slug}`}
                    className="group flex w-full flex-col gap-4 rounded-panel border border-line bg-surface p-7 transition-colors hover:border-strong hover:bg-raised"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex size-[42px] shrink-0 items-center justify-center rounded-button border border-strong bg-raised text-primary">
                        <Icon />
                      </span>
                      <Chip tone={roadmap ? 'dashed' : 'default'}>
                        {statusLabel[product.status]}
                      </Chip>
                    </div>
                    <span className="text-[17px] font-semibold text-primary">{product.name}</span>
                    <p className="m-0 text-[15px] leading-[1.6] text-muted">{product.summary}</p>
                    <div className="mt-auto flex items-center justify-between gap-3 pt-2">
                      <Chip>{product.pricing}</Chip>
                      <ArrowRightIcon
                        size={16}
                        className="shrink-0 text-dash transition-colors group-hover:text-primary"
                      />
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </Section>

      <Section alt>
        <div className="flex flex-col gap-10">
          <div data-reveal className="flex max-w-[760px] flex-col gap-4">
            <Eyebrow>{productsIndex.matrixEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productsIndex.matrixHeading}
            </h2>
            <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">
              {productsIndex.matrixLead}
            </p>
          </div>

          <ScrollableTable
            label={productsIndex.matrixHeading}
            data-reveal
            className="rounded-panel border border-line bg-surface"
          >
            <table className="w-full min-w-[820px] border-collapse text-left text-[15px] leading-[1.5]">
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="w-[28%] px-6 py-5 font-mono text-[11.5px] font-medium tracking-[0.1em] text-meta"
                  >
                    {productsIndex.matrixColumnLabel}
                  </th>
                  {products.map((product) => (
                    <th key={product.slug} scope="col" className="px-4 py-5 text-center align-bottom">
                      <span className="flex flex-col items-center gap-1.5">
                        <span className="font-mono text-[11.5px] font-medium tracking-[0.1em] text-secondary">
                          {product.name.replace('Vyom ', '').toUpperCase()}
                        </span>
                        {product.status === 'roadmap' ? (
                          <span className="font-mono text-[11px] tracking-[0.08em] text-meta">
                            ROADMAP
                          </span>
                        ) : null}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {capabilityMatrix.map((row) => (
                  <tr key={row.capability}>
                    <th
                      scope="row"
                      className="border-t border-line px-6 py-4 text-left align-middle font-medium text-primary"
                    >
                      {row.capability}
                    </th>
                    {products.map((product) => {
                      const has = row.products.includes(product.slug);
                      const planned = row.planned?.includes(product.slug) ?? false;
                      return (
                        <td
                          key={product.slug}
                          className="border-t border-line px-4 py-4 text-center align-middle"
                        >
                          {has ? (
                            <span className="inline-flex text-green">
                              <CheckIcon size={18} />
                              <span className="sr-only">Included in {product.name}</span>
                            </span>
                          ) : planned ? (
                            <span className="inline-flex flex-col items-center gap-1 text-meta">
                              <CheckIcon size={18} className="opacity-45" />
                              <span className="font-mono text-[11px] tracking-[0.08em]">
                                {productsIndex.plannedLabel.toUpperCase()}
                              </span>
                              <span className="sr-only">Planned for {product.name}</span>
                            </span>
                          ) : (
                            <>
                              <span aria-hidden="true" className="text-meta">
                                –
                              </span>
                              <span className="sr-only">Not in {product.name}</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollableTable>
        </div>
      </Section>
    </>
  );
}
