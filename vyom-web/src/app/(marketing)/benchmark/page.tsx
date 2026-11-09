import type { Metadata } from 'next';
import { benchmarkPage, benchmarkRuns } from '@/content/benchmark';
import { PageHero, Section, SectionHeading } from '@/components/ui';

export const metadata: Metadata = {
  title: benchmarkPage.title,
  description: benchmarkPage.description,
};

export default function BenchmarkPage() {
  return (
    <>
      <PageHero eyebrow={benchmarkPage.eyebrow} heading={benchmarkPage.heading} lead={benchmarkPage.lead}>
        <a
          href={benchmarkPage.methodLink.href}
          className="inline-flex min-h-11 items-center font-mono text-[12px] text-accent underline underline-offset-4"
        >
          {benchmarkPage.methodLink.label}
        </a>
      </PageHero>

      <Section>
        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <span className="font-mono text-[11px] font-medium tracking-[0.12em] text-meta uppercase">
              {benchmarkPage.task.label}
            </span>
            <p className="m-0 max-w-[820px] text-[18px] leading-[1.6] text-secondary">
              {benchmarkPage.task.value}
            </p>
            <p className="m-0 text-[14px] leading-[1.6] text-muted">{benchmarkPage.task.source}</p>
          </div>

          <div className="flex flex-col gap-5">
            <h2 className="m-0 text-[22px] leading-[1.25] font-semibold text-primary">
              {benchmarkPage.runsHeading}
            </h2>
            {benchmarkRuns.length ? (
              <ul className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-4 p-0">
                {benchmarkRuns.map((run) => (
                  <li key={`${run.date}-${run.model}`} className="flex flex-col gap-4 rounded-card border border-line bg-surface p-6">
                    <dl className="m-0 grid gap-3">
                      <div>
                        <dt className="font-mono text-[10px] tracking-[0.1em] text-meta uppercase">{benchmarkPage.runLabels.model}</dt>
                        <dd className="m-0 mt-1 break-words text-[16px] text-primary">{run.model}</dd>
                      </div>
                      <div>
                        <dt className="font-mono text-[10px] tracking-[0.1em] text-meta uppercase">{benchmarkPage.runLabels.task}</dt>
                        <dd className="m-0 mt-1 text-[15px] leading-[1.55] text-secondary">{run.task}</dd>
                      </div>
                      <div>
                        <dt className="font-mono text-[10px] tracking-[0.1em] text-meta uppercase">{benchmarkPage.runLabels.date}</dt>
                        <dd className="m-0 mt-1 font-mono text-[13px] text-secondary">{run.date}</dd>
                      </div>
                    </dl>
                    {run.resultHref ? (
                      <a href={run.resultHref} className="inline-flex min-h-11 items-center self-start font-mono text-[12px] text-accent underline underline-offset-4">
                        {benchmarkPage.resultLinkLabel}
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col gap-5 border-y border-hairline py-6">
                <p className="m-0 text-[15px] leading-[1.6] text-muted">{benchmarkPage.emptyState}</p>
                <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(min(180px,100%),1fr))] gap-3">
                  {Object.entries(benchmarkPage.unpublishedRun).map(([field, value]) => (
                    <div key={field} className="flex min-w-0 flex-col gap-1 rounded-card border border-line bg-surface p-4">
                      <dt className="font-mono text-[10px] tracking-[0.1em] text-meta uppercase">
                        {benchmarkPage.runLabels[field as keyof typeof benchmarkPage.runLabels]}
                      </dt>
                      <dd className="m-0 text-[14px] leading-[1.5] text-secondary">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
        </div>
      </Section>

      <Section id={benchmarkPage.method.id} alt flush>
        <div className="flex flex-col gap-8">
          <SectionHeading eyebrow={benchmarkPage.method.eyebrow} heading={benchmarkPage.method.heading} />
          <p className="m-0 max-w-[820px] text-[16px] leading-[1.65] text-secondary">{benchmarkPage.method.body}</p>
          <p className="m-0 max-w-[820px] text-[14px] leading-[1.6] text-muted">{benchmarkPage.method.limitation}</p>
          <span className="font-mono text-[11px] font-medium tracking-[0.12em] text-meta uppercase">
            {benchmarkPage.method.closingCitationLabel}
          </span>
          <ul className="m-0 flex list-none flex-wrap gap-x-6 gap-y-3 p-0">
            {benchmarkPage.method.sources.map((source) => (
              <li key={source.href}>
                <a href={source.href} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center font-mono text-[11px] text-accent underline underline-offset-4">
                  {source.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </Section>
    </>
  );
}