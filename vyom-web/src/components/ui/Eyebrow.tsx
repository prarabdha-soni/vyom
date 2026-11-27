import { cn } from '@/lib/cn';

/** Mono 12px uppercase label above a heading. */
export function Eyebrow({
  children,
  className,
}: {
  readonly children: string;
  readonly className?: string;
}) {
  return (
    <span
      className={cn(
        'font-mono text-[12px] font-medium tracking-[0.14em] text-meta uppercase',
        className,
      )}
    >
      {children}
    </span>
  );
}
