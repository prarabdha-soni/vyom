'use client';

import Link from 'next/link';
import { useActionState } from 'react';
import { verifyCopy } from '@/content/console';
import { cn } from '@/lib/cn';
import { createCase } from '@/lib/console/actions';
import { Field, FormNotice, SubmitButton, initialActionState, inputClass } from '../forms';

export function IntakeForm({ today, cancelHref }: { readonly today: string; readonly cancelHref: string }) {
  const [state, action] = useActionState(createCase, initialActionState);
  const copy = verifyCopy.intake;
  return (
    <form action={action} className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Field label={copy.channel}>
          <select name="channel" defaultValue={state.fields?.channel ?? 'safety_email'} className={inputClass}>
            {copy.channels.map((channel) => (
              <option key={channel.value} value={channel.value}>
                {channel.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={copy.receivedOn}>
          <input type="date" name="received_on" defaultValue={state.fields?.received_on ?? today} max={today} className={inputClass} />
        </Field>
        <Field label={copy.subject}>
          <input type="text" name="subject" defaultValue={state.fields?.subject} maxLength={200} className={inputClass} />
        </Field>
      </div>
      <Field label={copy.sourceText} hint={copy.sourceHint}>
        <textarea
          name="source_text"
          defaultValue={state.fields?.source_text}
          required
          minLength={20}
          maxLength={20000}
          rows={14}
          className={cn(inputClass, 'py-2.5 font-mono text-[13px] leading-[1.6]')}
        />
      </Field>
      <FormNotice state={state} />
      <div className="flex flex-wrap items-center gap-2">
        <SubmitButton pending="Creating…">{copy.submit}</SubmitButton>
        <Link href={cancelHref} className="inline-flex min-h-[44px] items-center rounded-control px-4 text-[14px] font-medium text-secondary hover:bg-raised">
          {copy.cancel}
        </Link>
      </div>
    </form>
  );
}
