import { hero } from '@/content/home';
import { ArrowRightIcon } from '@/components/icons';
import { SafetyWorkspace } from '@/components/mocks';
import { SkyWash } from '@/components/site';
import { ButtonLink, Container } from '@/components/ui';

export function Hero() {
  const { before, highlight, after } = hero.headline;

  return (
    <section id="top" className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="hero" />

      <Container className="relative flex flex-col items-center gap-[72px] pt-16 pb-16 sm:pt-[120px] sm:pb-[104px]">
        {/* Text block */}
        <div className="flex w-full max-w-[1080px] flex-col items-center gap-7 text-center">
          <span className="inline-flex items-center gap-[9px] rounded-full border border-strong bg-surface px-3 py-1.5 font-mono text-[12px] font-medium tracking-[0.08em] text-secondary">
            <span className="size-1.5 shrink-0 rounded-full bg-cta" />
            {hero.pill}
          </span>

          {/*
            One sentence, wrapping naturally. `text-balance` keeps the last
            line from stranding a single word.
          */}
          <h1 className="m-0 text-[clamp(34px,6vw,84px)] leading-[0.98] font-semibold tracking-[-0.042em] text-balance text-primary">
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
