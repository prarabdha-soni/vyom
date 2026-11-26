'use client';

import { useState, type ComponentProps, type ReactNode } from 'react';
import { useFormStatus } from 'react-dom';
import { Button, type ButtonVariant } from '@/components/ui';
import { cn } from '@/lib/cn';
import type { ActionState } from '@/lib/console/actions';

export const initialActionState: ActionState = { status: 'idle', message: null };

export const inputClass =
  'min-h-[40px] w-full rounded-control border border-button bg-surface px-3 text-[14px] text-primary placeholder:text-meta focus-visible:border-primary disabled:bg-raised disabled:text-muted';

export function SubmitButton({
  children,
  pending: pendingLabel,
  variant = 'panelPrimary',
  className,
  ...rest
}: {
  readonly children: ReactNode;
  readonly pending?: string;
  readonly variant?: ButtonVariant;
  readonly className?: string;
} & Omit<ComponentProps<'button'>, 'children' | 'className' | 'type'>) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" variant={variant} disabled={pending || rest.disabled} className={className} {...rest}>
      {pending && pendingLabel ? pendingLabel : children}
    </Button>
  );
}

/**
 * The result of the last submission, announced politely. Pass the record's
 * `revision` (version, status…) and the notice clears once another action
 * moves the record on, so a message never outlives what it describes.
 */
export function FormNotice({
  state: latest,
  revision,
  className,
}: {
  readonly state: ActionState;
  readonly revision?: string | number;
  readonly className?: string;
}) {
  const [seen, setSeen] = useState({ state: latest, revision });
  if (seen.state !== latest) setSeen({ state: latest, revision });
  const stale = seen.state === latest && revision !== undefined && seen.revision !== revision;
  const state = stale ? initialActionState : latest;
  if (state.status === 'idle' || !state.message) return <p role="status" className="sr-only" />;
  const tone =
    state.status === 'ok'
      ? 'border-green-line bg-green-soft text-green'
      : state.status === 'error'
        ? 'border-rose-line bg-rose-soft text-rose'
        : 'border-dashed border-dash bg-raised text-secondary';
  return (
    <p role={state.status === 'error' ? 'alert' : 'status'} className={cn('m-0 rounded-control border px-3 py-2 text-[13.5px] leading-[1.45]', tone, className)}>
      {state.message}
    </p>
  );
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  readonly label: string;
  readonly hint?: string;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <label className={cn('flex min-w-0 flex-col gap-1.5', className)}>
      <span className="text-[13px] font-medium text-secondary">{label}</span>
      {children}
      {hint ? <span className="text-[12.5px] leading-[1.4] text-meta">{hint}</span> : null}
    </label>
  );
}
