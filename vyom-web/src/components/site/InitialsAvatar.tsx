import { cn } from '@/lib/cn';

/** Initials in a bordered tile. No stock photography anywhere on this site. */
export function InitialsAvatar({
  name,
  filled,
}: {
  readonly name: string;
  /** Unfilled means the seat is open: dashed border, muted text. */
  readonly filled: boolean;
}) {
  // Skip connectors so "Quality & Validation Lead" reads QV, not Q&.
  const skip = new Set(['of', 'and', 'the', 'for', '&']);
  const initials = name
    .split(/\s+/)
    .filter((part) => part && !skip.has(part.toLowerCase()) && /^[a-z]/i.test(part))
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');

  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex size-14 shrink-0 items-center justify-center rounded-nested border font-mono text-[16px] font-medium tracking-[0.06em]',
        filled
          ? 'border-ink bg-ink text-on-ink'
          : 'border-dashed border-dash bg-surface text-meta',
      )}
    >
      {initials}
    </span>
  );
}
