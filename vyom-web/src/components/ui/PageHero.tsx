import type { ReactNode } from 'react';
import { SkyWash } from '@/components/site';
import { Container } from './Container';
import { Eyebrow } from './Eyebrow';

/** The standard hero for every page below the home page. */
export function PageHero({
  eyebrow,
  heading,
  lead,
  children,
  size = 'md',
}: {
  readonly eyebrow: string;
  readonly heading: string;
  readonly lead?: string;
  readonly children?: ReactNode;
  /** `lg` for the shorter statement headings that need more room. */
  readonly size?: 'md' | 'lg';
}) {
  return (
    <section className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="cta" />
      <Container className="relative flex flex-col gap-6 py-16 sm:py-24">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1
          className={
            size === 'lg'
              ? 'm-0 max-w-[980px] text-[clamp(32px,3.9vw,52px)] leading-[1.1] font-semibold tracking-[-0.03em] text-balance text-primary'
              : 'm-0 max-w-[920px] text-[clamp(36px,4.4vw,60px)] leading-[1.04] font-semibold tracking-[-0.03em] text-balance text-primary'
          }
        >
          {heading}
        </h1>
        {lead ? (
          <p className="m-0 max-w-[640px] text-[19px] leading-[1.6] text-pretty text-muted">
            {lead}
          </p>
        ) : null}
        {children}
      </Container>
    </section>
  );
}
