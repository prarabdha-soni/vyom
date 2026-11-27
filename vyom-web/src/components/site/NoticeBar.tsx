import { siteConfig } from '~/site.config';
import { notice } from '@/content/site';
import { Container } from '@/components/ui';

/** Sitewide concept-preview bar. Controlled by one flag in site.config.ts. */
export function NoticeBar() {
  if (!siteConfig.showNotice) return null;

  return (
    <div className="border-b border-line bg-alt">
      <Container className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 py-[9px] text-center font-mono text-[12px] tracking-[0.04em] text-muted">
        <span className="font-medium text-primary">{notice.label}</span>
        <span>{notice.text}</span>
      </Container>
    </div>
  );
}
