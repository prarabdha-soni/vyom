import type { Metadata } from 'next';
import { bookDemoPage } from '@/content/bookDemo';
import { CheckIcon } from '@/components/icons';
import { BenchmarkForm } from '@/components/contact/BenchmarkForm';
import { SkyWash } from '@/components/site';
import { Container, Eyebrow } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Book a demo',
  description:
    'Book a Vyom walkthrough for a hospital TPA desk or pharmacovigilance team. Sample data first, then a free retrospective benchmark if you want proof before price.',
};

export default function BookDemoPage() {
  return (
    <section className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="cta" />
      <Container className="relative py-16 sm:py-24">
        <div className="flex flex-wrap items-start gap-x-16 gap-y-12">
          <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-6">
            <Eyebrow>{bookDemoPage.eyebrow}</Eyebrow>
            <h1 className="m-0 text-[clamp(36px,4.4vw,56px)] leading-[1.05] font-semibold tracking-[-0.03em] text-balance text-primary">
              {bookDemoPage.heading}
            </h1>
            <p className="m-0 max-w-[560px] text-[19px] leading-[1.6] text-pretty text-muted">
              {bookDemoPage.lead}
            </p>
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {bookDemoPage.points.map((point) => (
                <li key={point} className="flex items-start gap-3 text-[15.5px] leading-[1.5] text-secondary">
                  <span className="mt-0.5 flex shrink-0 text-green">
                    <CheckIcon />
                  </span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 flex-[1_1_380px]">
            <BenchmarkForm />
          </div>
        </div>
      </Container>
    </section>
  );
}
