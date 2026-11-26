import type { Metadata } from 'next';
import { siteConfig } from '~/site.config';
import { contactPage } from '@/content/contact';
import { CheckIcon } from '@/components/icons';
import { BenchmarkForm } from '@/components/contact/BenchmarkForm';
import { SkyWash } from '@/components/site';
import { Container, Eyebrow } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Contact',
  description:
    'Become a Vyom design partner: a free retrospective benchmark on your own data, early pricing and input on the roadmap.',
};

export default function ContactPage() {
  return (
    <section className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="cta" />
      <Container className="relative py-16 sm:py-24">
        <div className="flex flex-wrap items-start gap-x-16 gap-y-12">
          <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-6">
            <Eyebrow>{contactPage.eyebrow}</Eyebrow>
            <h1 className="m-0 text-[clamp(36px,4.4vw,56px)] leading-[1.05] font-semibold tracking-[-0.03em] text-balance text-primary">
              {contactPage.heading}
            </h1>
            <p className="m-0 max-w-[560px] text-[19px] leading-[1.6] text-pretty text-muted">
              {contactPage.lead}
            </p>

            <div className="flex flex-col gap-4 border-t border-line pt-7">
              <span className="font-mono text-[11.5px] font-medium tracking-[0.12em] text-meta">
                {contactPage.benefitsHeading.toUpperCase()}
              </span>
              <ul className="m-0 flex list-none flex-col gap-5 p-0">
                {contactPage.benefits.map((benefit) => (
                  <li key={benefit.title} className="flex items-start gap-3">
                    <span className="mt-0.5 flex shrink-0 text-green">
                      <CheckIcon />
                    </span>
                    <span className="flex flex-col gap-1">
                      <span className="text-[16px] font-semibold text-primary">
                        {benefit.title}
                      </span>
                      <span className="text-[15px] leading-[1.6] text-muted">{benefit.body}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <span className="font-mono text-[12.5px] tracking-[0.06em] text-meta">
              {siteConfig.email} · {siteConfig.locationMono}
            </span>
          </div>

          <div className="min-w-0 flex-[1.1_1_440px]">
            <BenchmarkForm />
          </div>
        </div>
      </Container>
    </section>
  );
}
