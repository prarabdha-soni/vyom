import { siteConfig } from '~/site.config';
import { cta } from '@/content/home';
import { ArrowRightIcon } from '@/components/icons';
import { SkyWash } from '@/components/site';
import { ButtonLink, Container, Eyebrow } from '@/components/ui';

export function CallToAction() {
  return (
    <section id="benchmark" className="relative overflow-hidden border-b border-hairline">
      <SkyWash variant="cta" />
      <Container className="relative py-16 sm:py-28">
        <div
          data-reveal
          className="mx-auto flex max-w-[760px] flex-col items-center gap-6 text-center"
        >
          <Eyebrow>{cta.eyebrow}</Eyebrow>
          <h2 className="m-0 text-[clamp(36px,4vw,56px)] leading-[1.05] font-semibold tracking-[-0.03em] text-balance text-primary">
            {cta.heading}
          </h2>
          <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">{cta.lead}</p>

          <div className="flex flex-wrap justify-center gap-3">
            <ButtonLink href={cta.primary.href} size="lg">
              {cta.primary.label}
              <ArrowRightIcon />
            </ButtonLink>
            <ButtonLink href={cta.secondary.href} variant="secondary" size="lg">
              {cta.secondary.label}
            </ButtonLink>
          </div>

          <span className="font-mono text-[12.5px] tracking-[0.06em] text-meta">
            {siteConfig.email} · {siteConfig.locationMono}
          </span>
        </div>
      </Container>
    </section>
  );
}
