import type { Highlight } from '@/lib/gateway/types';

/**
 * Text with keyword highlights. Rule-based matches use the neutral mark
 * colour; only model-produced highlights may ever be blue, and none are today.
 */
export function Highlighted({
  text,
  highlights,
  tone = 'neutral',
}: {
  readonly text: string;
  readonly highlights: readonly Highlight[];
  /** `verified` marks source words a field was checked against. */
  readonly tone?: 'neutral' | 'verified';
}) {
  const markClass =
    tone === 'verified'
      ? 'rounded-[3px] bg-green-soft px-0.5 text-primary shadow-[inset_0_-1.5px_0_var(--color-green-fill)]'
      : 'rounded-[3px] bg-mark px-0.5 text-primary shadow-[inset_0_-1px_0_var(--color-strong)]';
  const sorted = [...highlights]
    .filter((h) => h.start >= 0 && h.end <= text.length && h.end > h.start)
    .sort((a, b) => a.start - b.start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const [index, h] of sorted.entries()) {
    if (h.start < cursor) continue;
    if (h.start > cursor) parts.push(text.slice(cursor, h.start));
    parts.push(
      <mark key={index} title={`${h.kind}: ${h.label}`} className={markClass}>
        {text.slice(h.start, h.end)}
      </mark>,
    );
    cursor = h.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return <>{parts}</>;
}
