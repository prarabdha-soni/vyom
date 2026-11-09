import type { Metadata } from 'next';
import { qualityPage, qualityMeta } from '@/content/quality';
import { ArrowRightIcon } from '@/components/icons';
import { ButtonLink, Chip, PageHero, Section, SectionHeading } from '@/components/ui';

export const metadata: Metadata = {
  title: qualityMeta.title,
  description: qualityMeta.description,
  robots: { index: false, follow: false },
};

export default function QualityPage() {
  return (
    <>
      <PageHero eyebrow={qualityPage.eyebrow} heading={qualityPage.heading} lead={qualityPage.lead}>
        <Chip tone="dashed">{qualityPage.informationalChip}</Chip>
      </PageHero>

      <Section alt>
        <div className="mx-auto w-full max-w-[900px]">
          <div className="flex flex-col gap-3 rounded-panel border border-strong bg-panel p-6 sm:p-8">
            <span className="font-mono text-[11px] font-medium tracking-[0.12em] text-meta uppercase">
              {qualityPage.notice.heading}
            </span>
            <p className="m-0 text-[16px] leading-[1.65] text-secondary">{qualityPage.notice.body}</p>
            <a
              href={qualityPage.notice.href}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-2 self-start font-mono text-[12px] text-accent underline underline-offset-4"
            >
              {qualityPage.notice.citation}
              <ArrowRightIcon />
            </a>
          </div>
        </div>
      </Section>

      <Section>
        <div className="flex flex-col gap-10">
          <SectionHeading
            eyebrow={qualityPage.readiness.eyebrow}
            heading={qualityPage.readiness.heading}
            lead={qualityPage.readiness.lead}
          />
          <ul className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-4 p-0">
            {qualityPage.areas.map((area) => (
              <li key={area.title} className="flex min-w-0 flex-col gap-3 rounded-card border border-line bg-surface p-6">
                <h2 className="m-0 text-[19px] leading-[1.25] font-semibold text-balance text-primary">
                  {area.title}
                </h2>
                <p className="m-0 text-[15px] leading-[1.6] text-muted">{area.body}</p>
                <a
                  href={area.href}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-auto inline-flex min-h-11 items-center font-mono text-[11px] text-accent underline underline-offset-4"
                >
                  {area.citation} · G.S.R. 922(E)
                </a>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section alt flush>
        <div className="flex flex-col items-start gap-6">
          <div className="flex flex-col gap-2">
            <p className="m-0 max-w-[820px] text-[16px] leading-[1.65] text-muted">{qualityPage.closing}</p>
            <a href={qualityPage.notice.href} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center self-start font-mono text-[11px] text-accent underline underline-offset-4">
              {qualityPage.closingCitation}
            </a>
          </div>
          <ButtonLink href={qualityPage.cta.href}>
            {qualityPage.cta.label}
            <ArrowRightIcon />
          </ButtonLink>
        </div>
      </Section>
    </>
  );
}