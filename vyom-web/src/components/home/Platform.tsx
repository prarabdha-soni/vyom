import Link from 'next/link';
import { platformModules } from '@/content/home';
import { getProduct, statusLabel } from '@/content/products';
import { ArrowRightIcon, CheckIcon, moduleIcons, productIcons } from '@/components/icons';
import { Chip, Section, SectionHeading } from '@/components/ui';

/** The three modules as large cards, then the public preview and the roadmap. */
export function Platform() {
  return (
    <Section id="platform" alt>
      <div className="flex flex-col gap-14">
        <SectionHeading
          eyebrow={platformModules.eyebrow}
          heading={platformModules.heading}
          lead={platformModules.lead}
        />

        <ul data-reveal className="m-0 grid list-none grid-cols-1 gap-4 p-0 lg:grid-cols-3">
          {platformModules.modules.map((module) => {
            const product = getProduct(module.product);
            const Icon = productIcons[product.slug];
            return (
              <li
                key={product.slug}
                className="flex min-w-0 flex-col gap-5 rounded-panel border border-line bg-surface p-7"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex size-[42px] shrink-0 items-center justify-center rounded-button border border-line bg-raised text-primary">
                    <Icon />
                  </span>
                  <span className="font-mono text-[11px] tracking-[0.12em] text-meta">{product.kicker}</span>
                </div>

                <div className="flex flex-col gap-2">
                  <h3 className="m-0 flex items-baseline gap-2 text-[30px] leading-none font-normal tracking-[-0.025em] text-primary">
                    <span aria-hidden="true" className="size-2 shrink-0 -translate-y-1.5 rounded-full bg-cta" />
                    {product.shortName}
                  </h3>
                  <p className="m-0 text-[16px] leading-[1.45] font-medium text-secondary">{product.headline}</p>
                </div>

                <ul className="m-0 flex list-none flex-col gap-2 p-0">
                  {module.points.map((point) => (
                    <li key={point} className="flex items-start gap-2.5 text-[14.5px] leading-[1.5] text-muted">
                      <CheckIcon size={16} className="mt-[3px] shrink-0 text-green" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>

                <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
                  <Chip tone="default" size="sm">
                    {statusLabel[product.status]}
                  </Chip>
                  <Link
                    href={`/products/${product.slug}`}
                    className="inline-flex min-h-[44px] items-center gap-1.5 text-[14px] font-medium text-primary hover:underline"
                  >
                    {platformModules.moduleLinkLabel} {product.name}
                    <ArrowRightIcon size={14} />
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>

        <ul data-reveal className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-2">
          {platformModules.more.map((item) => {
            const Icon = moduleIcons[item.icon];
            return (
              <li
                key={item.name}
                className="flex min-w-0 flex-wrap items-center gap-x-5 gap-y-3 rounded-panel border border-line bg-surface px-6 py-5"
              >
                <span className="flex size-[38px] shrink-0 items-center justify-center rounded-button border border-line bg-raised text-primary">
                  <Icon size={20} />
                </span>
                <div className="flex min-w-0 flex-[1_1_240px] flex-col gap-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-[16px] font-semibold text-primary">{item.name}</span>
                    <Chip tone="dashed" size="xs">
                      {item.chip}
                    </Chip>
                  </span>
                  <span className="text-[14px] leading-[1.5] text-muted">{item.body}</span>
                </div>
                {item.link ? (
                  <Link
                    href={item.link.href}
                    className="inline-flex min-h-[44px] items-center gap-1.5 text-[14px] font-medium text-primary hover:underline"
                  >
                    {item.link.label}
                    <ArrowRightIcon size={14} />
                  </Link>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    </Section>
  );
}
