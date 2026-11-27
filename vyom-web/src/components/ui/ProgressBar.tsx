import { cn } from '@/lib/cn';

export type BarTone = 'accent' | 'amber' | 'muted' | 'green' | 'ink' | 'rose';

const fills: Record<BarTone, string> = {
  accent: 'bg-accent',
  amber: 'bg-amber',
  muted: 'bg-dash',
  green: 'bg-green-fill',
  ink: 'bg-primary',
  rose: 'bg-rose',
};

/**
 * A plain CSS bar — no chart library. Decorative: the value it illustrates is
 * always printed as text beside it, so the bar itself is aria-hidden.
 */
export function ProgressBar({
  width,
  tone = 'accent',
  height = 6,
  className,
}: {
  /** Percentage, 0–100. */
  readonly width: number;
  readonly tone?: BarTone;
  readonly height?: 6 | 8;
  readonly className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, width));

  return (
    <div
      aria-hidden="true"
      className={cn('w-full bg-hairline', height === 6 ? 'h-1.5 rounded-[3px]' : 'h-2 rounded', className)}
    >
      <div
        className={cn('h-full min-w-[4px]', height === 6 ? 'rounded-[3px]' : 'rounded', fills[tone])}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
