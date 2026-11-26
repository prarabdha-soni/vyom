import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/**
 * Tone carries meaning: accent = AI, amber = a human decision, green =
 * verified or complete, rose = locked or overdue, muted = a neutral state
 * such as Draft, dashed = SAMPLE DATA and ROADMAP.
 */
export type ChipTone = 'default' | 'accent' | 'amber' | 'green' | 'rose' | 'muted' | 'dashed';
export type ChipSize = 'md' | 'sm' | 'xs';

const tones: Record<ChipTone, string> = {
  default: 'border-solid border-strong text-secondary',
  accent: 'border-solid border-accent-line bg-accent-tint text-accent',
  amber: 'border-solid border-amber-line bg-amber-soft text-amber',
  green: 'border-solid border-green-line bg-green-soft text-green',
  rose: 'border-solid border-rose-line bg-rose-soft text-rose',
  muted: 'border-solid border-transparent bg-raised text-secondary',
  dashed: 'border-dashed border-dash text-muted',
};

/** Sizes are a prop, not a className override, so they cannot lose a specificity race. */
const sizes: Record<ChipSize, string> = {
  md: 'px-[9px] py-[5px] text-[11px]',
  sm: 'px-2 py-1 text-[11px]',
  xs: 'px-1.5 py-0.5 text-[11px]',
};

/** Mono uppercase label, 6px radius. */
export function Chip({
  children,
  tone = 'default',
  size = 'md',
  className,
}: {
  readonly children: ReactNode;
  readonly tone?: ChipTone;
  readonly size?: ChipSize;
  readonly className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-chip border font-mono font-medium tracking-[0.08em] whitespace-nowrap',
        tones[tone],
        sizes[size],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** The SAMPLE DATA marker. Every mock screen carries one. */
export function SampleDataChip({ className }: { readonly className?: string }) {
  return (
    <span
      className={cn(
        'rounded-chip border border-dashed border-dash px-2 py-1 font-mono text-[11px] tracking-[0.1em] text-muted whitespace-nowrap',
        className,
      )}
    >
      SAMPLE DATA
    </span>
  );
}
