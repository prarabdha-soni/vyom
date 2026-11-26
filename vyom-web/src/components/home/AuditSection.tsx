import { auditSection } from '@/content/home';
import { ArrowRightIcon, CheckIcon } from '@/components/icons';
import { VendorScorecard } from '@/components/mocks';
import { ButtonLink, Eyebrow, Section } from '@/components/ui';

export function AuditSection() {
  return (
    <Section id="audit" alt>
      <div className="flex flex-wrap items-center gap-x-[72px] gap-y-14">
        <div data-reveal className="flex min-w-0 flex-[1_1_400px] flex-col gap-6">
          <Eyebrow>{auditSection.eyebrow}</Eyebrow>
          <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
            {auditSection.heading}
          </h2>
          <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">
            {auditSection.lead}
          </p>

          <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
            {auditSection.bullets.map((bullet) => (
              <li
                key={bullet}
                className="flex items-start gap-3 text-[16px] leading-[1.5] text-secondary"
              >
                <span className="mt-0.5 flex shrink-0 text-green">
                  <CheckIcon />
                </span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap gap-3 pt-2">
            <ButtonLink href={auditSection.cta.href} size="lg">
              {auditSection.cta.label}
              <ArrowRightIcon />
            </ButtonLink>
          </div>
        </div>

        <div data-reveal className="min-w-0 flex-[1.2_1_480px]">
          <VendorScorecard />
        </div>
      </div>
    </Section>
  );
}
