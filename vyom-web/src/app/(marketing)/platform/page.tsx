import type { Metadata } from 'next';
import { platformPage } from '@/content/platform';
import { securityIcons } from '@/components/icons';
import { ArchitectureFlow, AuditRecord } from '@/components/mocks';
import { Chip, PageHero, Section, SectionHeading } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Platform',
  description:
    'AI proposes, rules check, experts decide. How Vyom measures accuracy on your own data, what it records, and where that data lives.',
};

export default function PlatformPage() {
  const { principle, architecture, measurement, evaluation, auditTrail, security } = platformPage;

  return (
    <>
      <PageHero
        eyebrow={platformPage.eyebrow}
        heading={platformPage.heading}
        lead={platformPage.lead}
      />

      {/* The principle */}
      <Section alt>
        <div className="flex flex-col gap-12">
          <SectionHeading eyebrow={principle.eyebrow} heading={principle.heading} />
          <div data-reveal className="flex flex-wrap items-start gap-x-16 gap-y-10">
            <p className="m-0 min-w-0 flex-[1_1_380px] text-[19px] leading-[1.6] text-pretty text-secondary">
              {principle.body}
            </p>
            <ul className="m-0 flex min-w-0 flex-[1_1_380px] list-none flex-col gap-3 p-0">
              {principle.points.map((point) => (
                <li
                  key={point.title}
                  className="flex flex-col gap-1.5 rounded-card border border-line bg-surface px-6 py-5"
                >
                  <span className="text-[16px] font-semibold text-primary">{point.title}</span>
                  <span className="text-[15px] leading-[1.55] text-muted">{point.body}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* Architecture */}
      <Section>
        <div className="flex flex-col gap-10">
          <SectionHeading
            eyebrow={architecture.eyebrow}
            heading={architecture.heading}
            lead={architecture.lead}
          />
          <div
            data-reveal
            className="overflow-hidden rounded-panel border border-strong bg-panel"
          >
            <ArchitectureFlow />
          </div>
        </div>
      </Section>

      {/* What we measure */}
      <Section id="evaluation" alt>
        <div className="flex flex-col gap-10">
          <SectionHeading
            eyebrow={measurement.eyebrow}
            heading={measurement.heading}
            lead={measurement.lead}
          />
          <ul
            data-reveal
            className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-4 p-0"
          >
            {measurement.metrics.map((metric) => (
              <li
                key={metric.name}
                className="flex flex-col gap-3 rounded-card border border-line bg-surface p-6"
              >
                <span className="text-[19px] leading-[1.25] font-semibold tracking-[-0.01em] text-balance text-primary">
                  {metric.name}
                </span>
                <p className="m-0 text-[15px] leading-[1.6] text-muted">{metric.body}</p>
                {/* Each card says it is a measure, not a result. */}
                <Chip tone="default" className="mt-auto self-start">
                  {measurement.badge}
                </Chip>
              </li>
            ))}
          </ul>

          <div
            data-reveal
            className="flex flex-col gap-2.5 rounded-card border border-strong bg-surface p-7"
          >
            <span className="font-mono text-[12px] font-medium tracking-[0.14em] text-meta uppercase">
              {evaluation.eyebrow}
            </span>
            <span className="text-[21px] leading-[1.25] font-semibold tracking-[-0.01em] text-primary">
              {evaluation.heading}
            </span>
            <p className="m-0 max-w-[760px] text-[16px] leading-[1.6] text-muted">
              {evaluation.body}
            </p>
          </div>
        </div>
      </Section>

      {/* Audit trail */}
      <Section>
        <div className="flex flex-wrap items-start gap-x-16 gap-y-10">
          <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-4">
            <SectionHeading
              eyebrow={auditTrail.eyebrow}
              heading={auditTrail.heading}
              lead={auditTrail.lead}
            />
          </div>
          <div data-reveal className="min-w-0 flex-[1.2_1_460px]">
            <AuditRecord />
          </div>
        </div>
      </Section>

      {/* Security and data */}
      <Section id="security" alt>
        <div className="flex flex-col gap-10">
          <SectionHeading eyebrow={security.eyebrow} heading={security.heading} />
          <ul
            data-reveal
            className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-4 p-0"
          >
            {security.items.map((item) => {
              const Icon = securityIcons[item.icon];
              return (
                <li
                  key={item.title}
                  className="flex flex-col gap-3 rounded-card border border-line bg-surface p-6"
                >
                  <span className="flex size-[42px] shrink-0 items-center justify-center rounded-button border border-strong bg-raised text-primary">
                    <Icon />
                  </span>
                  <span className="text-[17px] font-semibold text-primary">{item.title}</span>
                  <p className="m-0 text-[15px] leading-[1.6] text-muted">{item.body}</p>
                </li>
              );
            })}
          </ul>
        </div>
      </Section>
    </>
  );
}
