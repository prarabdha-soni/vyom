import { howWeStart } from '@/content/home';
import { Chip, Eyebrow, Section } from '@/components/ui';
import { cn } from '@/lib/cn';

export function HowWeStart() {
  return (
    <Section id="proof">
      <div className="flex flex-col gap-12">
        <div data-reveal className="flex max-w-[760px] flex-col gap-4">
          <Eyebrow>{howWeStart.eyebrow}</Eyebrow>
          <h2 className="m-0 text-[clamp(32px,3.3vw,46px)] leading-[1.08] font-semibold tracking-[-0.025em] text-balance text-primary">
            {howWeStart.heading}
          </h2>
          <p className="m-0 text-[18px] leading-[1.6] text-pretty text-muted">{howWeStart.lead}</p>
        </div>

        <ol data-reveal className="m-0 flex list-none flex-wrap gap-4 p-0">
          {howWeStart.stages.map((stage) => (
            <li
              key={stage.number}
              className={cn(
                'flex min-w-0 flex-[1_1_300px] flex-col gap-3.5 rounded-panel border bg-surface p-7',
                stage.tone === 'accent' ? 'border-strong' : 'border-line',
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span
                  className={cn(
                    'text-[44px] leading-none font-semibold tracking-[-0.03em]',
                    'text-primary',
                  )}
                >
                  {stage.number}
                </span>
                <Chip>{stage.chip}</Chip>
              </div>
              <span className="text-[22px] font-semibold text-primary">{stage.title}</span>
              <p className="m-0 text-[15.5px] leading-[1.6] text-muted">{stage.body}</p>
            </li>
          ))}
        </ol>

        <div data-reveal className="flex flex-col gap-3.5">
          <span className="font-mono text-[11.5px] font-medium tracking-[0.12em] text-meta">
            {howWeStart.targetsLabel}
          </span>
          <ul className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-px overflow-hidden rounded-card border border-line bg-line p-0">
            {howWeStart.targets.map((target) => (
              <li key={target.value} className="flex flex-col gap-1.5 bg-alt px-6 py-[22px]">
                <span className="text-[30px] leading-[1.1] font-semibold tracking-[-0.02em] text-primary">
                  {target.value}
                </span>
                <span className="text-[14.5px] leading-[1.5] text-muted">{target.label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}
