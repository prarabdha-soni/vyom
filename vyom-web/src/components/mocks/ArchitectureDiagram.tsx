import { architecture } from '@/content/platform';
import { ArrowRightIcon } from '@/components/icons';
import { cn } from '@/lib/cn';

const flowTone = {
  accent: 'border-accent-line text-accent',
  amber: 'border-amber-line text-amber',
  default: 'border-line text-secondary',
} as const;

/**
 * The five-stage pipeline over the four things that hold it up, shown on
 * /platform. Drawn with HTML/CSS boxes rather than SVG so it reflows on a
 * phone and the labels stay selectable text.
 */
export function ArchitectureFlow() {
  return (
    <div className="flex flex-col gap-5 px-[22px] py-6">
        <ol className="m-0 flex list-none flex-wrap items-stretch gap-2 p-0">
          {architecture.flow.map((stage, index) => (
            <li key={stage.title} className="flex min-w-0 flex-[1_1_120px] items-center gap-2">
              <span
                className={cn(
                  'flex min-h-[56px] w-full items-center justify-center rounded-nested border bg-surface px-3 text-center text-[15px] font-semibold',
                  flowTone[stage.tone],
                )}
              >
                {stage.title}
              </span>
              {index < architecture.flow.length - 1 ? (
                <ArrowRightIcon size={16} className="hidden shrink-0 text-dash sm:block" />
              ) : null}
            </li>
          ))}
        </ol>

        <div className="flex flex-col gap-3 rounded-nested border border-dashed border-dash p-4">
          <span className="font-mono text-[11px] tracking-[0.1em] text-meta">
            {architecture.foundationLabel}
          </span>
          <ul className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(170px,100%),1fr))] gap-3 p-0">
            {architecture.foundation.map((item) => (
              <li
                key={item.title}
                className="flex flex-col gap-1 rounded-chip border border-line bg-surface px-3.5 py-3"
              >
                <span className="text-[14px] font-semibold text-primary">{item.title}</span>
                <span className="text-[12.5px] leading-[1.45] text-muted">{item.body}</span>
              </li>
            ))}
          </ul>
        </div>
    </div>
  );
}
