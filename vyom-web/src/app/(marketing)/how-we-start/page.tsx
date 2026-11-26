import type { Metadata } from 'next';
import { howWeStartPage } from '@/content/howWeStart';
import { ArrowRightIcon, CheckIcon, PlusIcon } from '@/components/icons';
import { ButtonLink, Chip, PageHero, Section, SectionHeading } from '@/components/ui';
import { cn } from '@/lib/cn';

export const metadata: Metadata = {
  title: 'How we start',
  description:
    'A free retrospective benchmark on your own data, then an eight-week parallel run, then production pricing with the targets written into the contract.',
};

export default function HowWeStartPage() {
  return (
    <>
      <PageHero
        eyebrow={howWeStartPage.eyebrow}
        heading={howWeStartPage.heading}
        lead={howWeStartPage.lead}
      >
        <div className="flex flex-wrap gap-3 pt-2">
          <ButtonLink href="/contact" size="lg">
            Get a free benchmark
            <ArrowRightIcon />
          </ButtonLink>
        </div>
      </PageHero>

      {/* The three stages, in depth */}
      <Section alt>
        <div className="flex flex-col gap-12">
          <SectionHeading heading={howWeStartPage.stagesHeading} />

          <ol className="m-0 flex list-none flex-col gap-4 p-0">
            {howWeStartPage.stages.map((stage) => (
              <li
                key={stage.number}
                data-reveal
                className={cn(
                  'flex flex-wrap gap-x-16 gap-y-8 rounded-panel border bg-surface p-7 sm:p-10',
                  stage.tone === 'accent' ? 'border-strong' : 'border-line',
                )}
              >
                <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      className={cn(
                        'text-[44px] leading-none font-semibold tracking-[-0.03em]',
                        'text-primary',
                      )}
                    >
                      {stage.number}
                    </span>
                    <Chip>{stage.chip}</Chip>
                  </div>
                  <h3 className="m-0 text-[26px] leading-[1.2] font-semibold tracking-[-0.015em] text-balance text-primary">
                    {stage.title}
                  </h3>
                  <p className="m-0 text-[16px] leading-[1.6] text-muted">{stage.summary}</p>
                  <p className="m-0 mt-auto border-t border-line pt-4 text-[14.5px] leading-[1.55] text-secondary">
                    <span className="font-mono text-[11px] tracking-[0.1em] text-meta">
                      {howWeStartPage.commitmentLabel}
                    </span>
                    <br />
                    {stage.commitment}
                  </p>
                </div>

                <div className="flex min-w-0 flex-[1.2_1_380px] flex-col gap-6">
                  <div className="flex flex-col gap-2">
                    <span className="font-mono text-[11px] tracking-[0.1em] text-meta">
                      {howWeStartPage.needLabel}
                    </span>
                    <p className="m-0 text-[15.5px] leading-[1.6] text-secondary">
                      {stage.whatWeNeed}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2.5">
                    <span className="font-mono text-[11px] tracking-[0.1em] text-meta">
                      {howWeStartPage.getLabel}
                    </span>
                    <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
                      {stage.whatYouGet.map((item) => (
                        <li
                          key={item}
                          className="flex items-start gap-3 text-[15.5px] leading-[1.5] text-secondary"
                        >
                          <span className="mt-0.5 flex shrink-0 text-green">
                            <CheckIcon />
                          </span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      {/* FAQ */}
      <Section>
        <div className="flex flex-col gap-10">
          <SectionHeading
            eyebrow={howWeStartPage.faq.eyebrow}
            heading={howWeStartPage.faq.heading}
          />
          {/* Native details/summary: keyboard-operable with no JavaScript. */}
          <ul data-reveal className="m-0 flex max-w-[860px] list-none flex-col gap-3 p-0">
            {howWeStartPage.faq.items.map((item) => (
              <li key={item.question}>
                <details className="group rounded-card border border-line bg-surface open:border-strong">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-6 py-5 text-[17px] font-semibold text-primary [&::-webkit-details-marker]:hidden">
                    {item.question}
                    <span
                      aria-hidden="true"
                      className="flex size-6 shrink-0 items-center justify-center text-primary transition-transform duration-200 group-open:rotate-45 motion-reduce:transition-none"
                    >
                      <PlusIcon />
                    </span>
                  </summary>
                  <p className="m-0 max-w-[720px] px-6 pb-6 text-[16px] leading-[1.65] text-muted">
                    {item.answer}
                  </p>
                </details>
              </li>
            ))}
          </ul>
        </div>
      </Section>
    </>
  );
}
