'use client';

import { useRouter } from 'next/navigation';
import { useActionState, useEffect, useRef, useState } from 'react';
import { literatureOutcomes, radarCopy } from '@/content/console';
import { cn } from '@/lib/cn';
import { decideLiterature, runSweep } from '@/lib/console/actions';
import { Field, FormNotice, SubmitButton, initialActionState, inputClass } from '../forms';

function typing(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  return Boolean(element?.closest('input, textarea, select, [contenteditable="true"]'));
}

/** J and K move through the queue. */
export function ReviewKeys({ previous, next }: { readonly previous: string | null; readonly next: string | null }) {
  const router = useRouter();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return;
      const key = event.key.toLowerCase();
      if (key === 'j' && next) router.push(next);
      if (key === 'k' && previous) router.push(previous);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [router, previous, next]);
  return null;
}

/** The four outcomes as radio cards, with V S N E shortcuts. */
export function DecisionForm({
  stateId,
  decisionId,
  suggested,
  urgent,
  nextStateId,
}: {
  readonly stateId: number;
  readonly decisionId: number;
  readonly suggested: string | null;
  /** The screen's band was RED_ESCALATE: closing as not relevant needs a reason. */
  readonly urgent: boolean;
  readonly nextStateId: number | null;
}) {
  const [state, action] = useActionState(decideLiterature, initialActionState);
  const [choice, setChoice] = useState<string>('');
  const form = useRef<HTMLFormElement>(null);
  const copy = radarCopy.review;
  // Mirrors Vyom OS: escalating, or closing an urgent article as not relevant, needs a reason.
  const reasonRule = choice === 'escalated' ? 'escalated' : choice === 'not_relevant' && urgent ? 'urgent' : 'optional';

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return;
      const match = literatureOutcomes.find((outcome) => outcome.key.toLowerCase() === event.key.toLowerCase());
      if (match) {
        setChoice(match.value);
        form.current?.querySelector<HTMLInputElement>(`input[value="${match.value}"]`)?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <form ref={form} action={action} className="flex flex-col gap-4">
      <input type="hidden" name="state_id" value={stateId} />
      <input type="hidden" name="decision_id" value={decisionId} />
      {nextStateId ? <input type="hidden" name="next" value={nextStateId} /> : null}
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-2 text-[13px] font-medium text-secondary">{copy.decision}</legend>
        {literatureOutcomes.map((outcome) => {
          const selected = choice === outcome.value;
          return (
            <label
              key={outcome.value}
              className={cn(
                'flex cursor-pointer items-start gap-3 rounded-button border px-3 py-2.5 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent',
                selected ? 'border-amber-line bg-amber-soft' : 'border-line hover:border-strong',
              )}
            >
              <input
                type="radio"
                name="outcome"
                value={outcome.value}
                checked={selected}
                onChange={() => setChoice(outcome.value)}
                required
                className="sr-only"
              />
              <span
                aria-hidden="true"
                className={cn(
                  'mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-chip border font-mono text-[11.5px] font-medium',
                  selected ? 'border-amber bg-amber text-on-ink' : 'border-strong text-meta',
                )}
              >
                {outcome.key}
              </span>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="flex flex-wrap items-center gap-2">
                  <span className={cn('text-[14px] font-medium', selected ? 'text-amber' : 'text-primary')}>{outcome.label}</span>
                  {suggested === outcome.value ? (
                    <span className="rounded-chip bg-raised px-1.5 py-0.5 font-mono text-[10.5px] tracking-[0.06em] text-secondary">
                      {copy.suggested}
                    </span>
                  ) : null}
                </span>
                <span className="text-[12.5px] leading-[1.4] text-meta">{outcome.hint}</span>
              </span>
            </label>
          );
        })}
      </fieldset>
      <Field label={copy.reason} hint={copy.reasonHint[reasonRule]}>
        <textarea
          name="reason"
          defaultValue={state.fields?.reason}
          required={reasonRule !== 'optional'}
          rows={3}
          maxLength={2000}
          className={cn(inputClass, 'py-2 leading-[1.45]')}
        />
      </Field>
      <FormNotice state={state} />
      <SubmitButton pending="Recording…" disabled={!choice}>
        {copy.submit}
      </SubmitButton>
      <p className="m-0 font-mono text-[11px] leading-[1.5] text-meta">{copy.shortcuts}</p>
    </form>
  );
}

export function SweepButton() {
  const [state, action] = useActionState(runSweep, initialActionState);
  return (
    <form action={action} className="flex flex-col items-end gap-2">
      <SubmitButton variant="panel" pending={radarCopy.sweep.running}>
        {radarCopy.sweep.label}
      </SubmitButton>
      <FormNotice state={state} className="max-w-[360px]" />
    </form>
  );
}
