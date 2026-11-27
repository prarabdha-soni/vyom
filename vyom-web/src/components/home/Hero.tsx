import Link from 'next/link';
import { siteConfig } from '~/site.config';
import { hero } from '@/content/home';
import { ArrowRightIcon, GridIcon } from '@/components/icons';
import { SafetyWorkspace } from '@/components/mocks';
import { SkyWash } from '@/components/site';
import { ButtonLink, Container } from '@/components/ui';

const PILL =
  'inline-flex items-center gap-[9px] rounded-full border border-strong bg-surface px-3 py-1.5 font-mono text-[12px] font-medium tracking-[0.08em] text-secondary';

export function Hero() {
  const { before, highlight, after } = hero.headline;

  return (
    <section id="top" className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="hero" />

      <Container className="relative flex flex-col items-center gap-[72px] pt-16 pb-16 sm:pt-[120px] sm:pb-[104px]">
        {/* Text block */}
        <div className="flex w-full max-w-[1080px] flex-col items-center gap-7 text-center">
          {siteConfig.sampleWorkspace ? (
            /*
              The way into the product, so it leads the hero: a large card-pill with
              a soft sunlight halo (the marketing call-to-action colour). It opens
              the sample dashboard directly; no sign-up, nothing is saved.
            */
            <Link
              href={hero.sampleWorkspace.href}
              className="group mb-2 inline-flex min-h-[64px] max-w-full items-center gap-4 rounded-full border border-strong bg-surface py-2 pr-2 pl-6 text-left shadow-[var(--shadow-pop)] ring-[5px] ring-cta/30 transition-[border-color,box-shadow] duration-150 hover:border-dash hover:ring-cta/55 sm:pl-2"
            >
              <span
                aria-hidden="true"
                className="hidden size-12 shrink-0 place-items-center rounded-full border border-hairline bg-alt text-primary sm:grid"
              >
                <GridIcon size={20} />
              </span>
              <span className="flex min-w-0 flex-col gap-0.5 sm:pr-2">
                <span className="text-[17px] leading-[1.25] font-semibold tracking-[-0.01em] text-primary sm:text-[18px]">
                  {hero.sampleWorkspace.label}
                </span>{' '}
                <span className="text-[13.5px] leading-[1.35] text-muted">{hero.sampleWorkspace.detail}</span>
              </span>
              <span
                aria-hidden="true"
                className="grid size-11 shrink-0 place-items-center rounded-full bg-ink text-on-ink transition-transform duration-150 group-hover:translate-x-0.5"
              >
                <ArrowRightIcon size={18} />
              </span>
            </Link>
          ) : null}

          <span className={PILL}>
            <span className="size-1.5 shrink-0 rounded-full bg-cta" />
            {hero.pill}
          </span>

          {/*
            One sentence, wrapping naturally. `text-balance` keeps the last
            line from stranding a single word.
          */}
          <h1 className="m-0 text-[clamp(32px,4.6vw,64px)] leading-[1.02] font-semibold tracking-[-0.038em] text-balance text-primary">
            {before}
            <span className="underline decoration-cta decoration-[0.08em] underline-offset-[0.14em] [text-decoration-skip-ink:none]">
              {highlight}
            </span>
            {after}
          </h1>

          <p className="m-0 max-w-[700px] text-[20px] leading-[1.6] text-pretty text-muted">
            {hero.subline}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href={hero.primaryCta.href} size="lg">
              {hero.primaryCta.label}
              <ArrowRightIcon />
            </ButtonLink>
            <ButtonLink href={hero.secondaryCta.href} variant="secondary" size="lg">
              {hero.secondaryCta.label}
            </ButtonLink>
          </div>

          <p className="m-0 max-w-[680px] font-mono text-[12.5px] leading-[1.6] tracking-[0.02em] text-pretty text-meta">
            {hero.footnote}
          </p>
        </div>

        {/* Workspace preview, below the text */}
        <div className="w-full max-w-[1080px]">
          <SafetyWorkspace />
        </div>
      </Container>
    </section>
  );
}
