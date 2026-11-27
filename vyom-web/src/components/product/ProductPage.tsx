import Link from 'next/link';
import type { Product } from '@/content/products';
import { getProductNeighbours, statusLabel } from '@/content/products';
import { ArrowRightIcon, CheckIcon, productIcons } from '@/components/icons';
import { SkyWash } from '@/components/site';
import { ButtonLink, Chip, Container, Eyebrow, Section } from '@/components/ui';
import { productPage } from '@/content/productPage';
import { SampleScreen } from './SampleScreen';
import { cn } from '@/lib/cn';

/** One template, driven entirely by the product's entry in products.ts. */
export function ProductPage({ product }: { readonly product: Product }) {
  const Icon = productIcons[product.slug];
  const { previous, next } = getProductNeighbours(product.slug);
  const roadmap = product.status === 'roadmap';

  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-hairline">
        <SkyWash variant="cta" />
        <Container className="relative flex flex-col gap-7 py-16 sm:py-24">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex size-[42px] shrink-0 items-center justify-center rounded-button border border-strong bg-surface text-primary">
              <Icon />
            </span>
            <span className="text-[17px] font-semibold text-primary">{product.name}</span>
            <Chip tone={roadmap ? 'dashed' : 'default'}>{statusLabel[product.status]}</Chip>
          </div>

          <h1 className="m-0 max-w-[920px] text-[clamp(36px,4.4vw,60px)] leading-[1.04] font-semibold tracking-[-0.03em] text-balance text-primary">
            {product.headline}
          </h1>

          <p className="m-0 max-w-[640px] text-[19px] leading-[1.6] text-pretty text-muted">
            {product.description}
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <ButtonLink href={productPage.cta.href} size="lg">
              {roadmap ? productPage.cta.roadmapLabel : productPage.cta.label}
              <ArrowRightIcon />
            </ButtonLink>
            <span className="flex min-h-[52px] items-center gap-2 font-mono text-[12.5px] tracking-[0.06em]">
              <span className="text-meta">{productPage.pricingLabel}</span>
              <span aria-hidden="true" className="text-meta">
                ·
              </span>
              <span className="text-secondary">{product.pricingUnit}</span>
            </span>
          </div>
        </Container>
      </section>

      {/* Problem */}
      <Section alt>
        <div data-reveal className="flex max-w-[760px] flex-col gap-4">
          <Eyebrow>{productPage.problemEyebrow}</Eyebrow>
          <p className="m-0 text-[clamp(24px,2.6vw,34px)] leading-[1.25] font-semibold tracking-[-0.02em] text-balance text-primary">
            {product.problem}
          </p>
        </div>
      </Section>

      {/* Capabilities */}
      <Section>
        <div data-reveal className="flex flex-wrap items-start gap-x-16 gap-y-10">
          <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-4">
            <Eyebrow>{productPage.capabilitiesEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productPage.capabilitiesHeading}
            </h2>
          </div>
          <ul className="m-0 grid min-w-0 flex-[1.4_1_480px] list-none grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-x-10 gap-y-3.5 p-0">
            {product.capabilities.map((capability) => (
              <li
                key={capability}
                className="flex items-start gap-3 text-[15.5px] leading-[1.5] text-secondary"
              >
                <span className="mt-0.5 flex shrink-0 text-green">
                  <CheckIcon />
                </span>
                <span>{capability}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* How it works */}
      <Section alt>
        <div className="flex flex-col gap-12">
          <div data-reveal className="flex max-w-[760px] flex-col gap-4">
            <Eyebrow>{productPage.stepsEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productPage.stepsHeading}
            </h2>
          </div>
          <ol data-reveal className="m-0 flex list-none flex-wrap gap-4 p-0">
            {product.steps.map((step, index) => (
              <li
                key={step.title}
                className="flex min-w-0 flex-[1_1_220px] flex-col gap-3.5 rounded-card border border-line bg-surface p-6"
              >
                <span className="font-mono text-[12px] font-medium tracking-[0.1em] text-meta">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="text-[19px] font-semibold text-primary">{step.title}</span>
                <p className="m-0 text-[15px] leading-[1.6] text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      {/* Sample screen */}
      <Section>
        <div className="flex flex-col gap-10">
          <div data-reveal className="flex max-w-[760px] flex-col gap-4">
            <Eyebrow>{productPage.sampleEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productPage.sampleHeading}
            </h2>
            <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">
              {productPage.sampleLead}
            </p>
          </div>
          <div data-reveal>
            <SampleScreen slug={product.slug} />
          </div>
        </div>
      </Section>

      {/* Targets */}
      <Section alt>
        <div className="flex flex-col gap-10">
          <div data-reveal className="flex max-w-[760px] flex-col gap-4">
            <Eyebrow>{productPage.targetsEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productPage.targetsHeading}
            </h2>
            <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">
              {productPage.targetsLead}
            </p>
          </div>
          <ul
            data-reveal
            className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-px overflow-hidden rounded-card border border-line bg-line p-0"
          >
            {product.targets.map((target) => (
              <li key={target} className="flex flex-col gap-2.5 bg-alt px-6 py-[22px]">
                {/* Every figure on this page is a goal, and says so. */}
                <Chip tone="dashed">TARGET</Chip>
                <span className="text-[17px] leading-[1.4] text-primary">{target}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* Who it's for */}
      <Section>
        <div data-reveal className="flex flex-wrap items-start gap-x-16 gap-y-8">
          <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-4">
            <Eyebrow>{productPage.audienceEyebrow}</Eyebrow>
            <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
              {productPage.audienceHeading}
            </h2>
          </div>
          <ul className="m-0 flex min-w-0 flex-[1.4_1_480px] list-none flex-col gap-3 p-0">
            {product.audience.map((who) => (
              <li
                key={who}
                className="flex items-start gap-3 rounded-card border border-line bg-surface px-6 py-5 text-[16px] leading-[1.5] text-secondary"
              >
                <span className="mt-0.5 flex shrink-0 text-green">
                  <CheckIcon />
                </span>
                <span>{who}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* Previous / next */}
      <nav aria-label="More products" className="border-b border-hairline bg-alt">
        <Container className="grid grid-cols-1 gap-px overflow-hidden py-0 sm:grid-cols-2">
          <ProductNeighbour product={previous} direction="previous" />
          <ProductNeighbour product={next} direction="next" />
        </Container>
      </nav>
    </>
  );
}

function ProductNeighbour({
  product,
  direction,
}: {
  readonly product: Product | null;
  readonly direction: 'previous' | 'next';
}) {
  const isNext = direction === 'next';

  if (!product) {
    // Keeps the two-column grid even at the ends of the list.
    return <div aria-hidden="true" className="hidden sm:block" />;
  }

  return (
    <Link
      href={`/products/${product.slug}`}
      className={cn(
        'group flex flex-col gap-2 border-hairline py-9 transition-colors hover:bg-surface',
        isNext ? 'sm:items-end sm:border-l sm:pl-10 sm:text-right' : 'sm:pr-10',
      )}
    >
      <span className="font-mono text-[11.5px] font-medium tracking-[0.12em] text-meta">
        {isNext ? 'NEXT' : 'PREVIOUS'}
      </span>
      <span className="flex items-center gap-2.5 text-[21px] font-semibold tracking-[-0.01em] text-primary">
        {!isNext ? <ArrowRightIcon size={18} className="rotate-180 text-primary" /> : null}
        {product.name}
        {isNext ? <ArrowRightIcon size={18} className="text-primary" /> : null}
      </span>
      <span className="max-w-[420px] text-[15px] leading-[1.5] text-muted">{product.summary}</span>
    </Link>
  );
}
