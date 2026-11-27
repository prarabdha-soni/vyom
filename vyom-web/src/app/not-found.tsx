import Link from 'next/link';
import { notFoundPage } from '@/content/legal';
import { ArrowRightIcon } from '@/components/icons';
import { Footer, Header, NoticeBar, SkyWash } from '@/components/site';
import { Container, Eyebrow } from '@/components/ui';

export default function NotFound() {
  return (
    <>
      <NoticeBar />
      <Header />
      <main id="main">
        <section className="relative overflow-hidden border-b border-hairline">
          <SkyWash variant="cta" />
          <Container className="relative flex flex-col gap-7 py-24 sm:py-32">
            <div className="flex flex-col gap-5">
              <span className="font-mono text-[clamp(56px,9vw,104px)] leading-none font-medium tracking-[-0.04em] text-primary">
                {notFoundPage.code}
              </span>
              <Eyebrow>{notFoundPage.eyebrow}</Eyebrow>
              <h1 className="m-0 max-w-[720px] text-[clamp(32px,3.9vw,52px)] leading-[1.08] font-semibold tracking-[-0.03em] text-balance text-primary">
                {notFoundPage.heading}
              </h1>
              <p className="m-0 max-w-[560px] text-[18px] leading-[1.6] text-pretty text-muted">
                {notFoundPage.lead}
              </p>
            </div>

            <nav aria-label="Main pages">
              <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
                {notFoundPage.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="flex min-h-[44px] items-center gap-2 rounded-button border border-button px-4 text-[15px] font-medium text-secondary transition-colors hover:border-strong hover:bg-surface hover:text-primary"
                    >
                      {link.label}
                      <ArrowRightIcon size={15} className="text-primary" />
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </Container>
        </section>
      </main>
      <Footer />
    </>
  );
}
