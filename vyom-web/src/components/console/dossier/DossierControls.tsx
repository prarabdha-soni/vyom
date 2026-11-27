'use client';

import Link from 'next/link';
import { useActionState } from 'react';
import { dossierCopy } from '@/content/console';
import { cn } from '@/lib/cn';
import { createReport, signOffReport, updateSection } from '@/lib/console/actions';
import { Field, FormNotice, SubmitButton, initialActionState, inputClass } from '../forms';

const copy = dossierCopy;

export function CreateReportForm({
  products,
  today,
}: {
  readonly products: readonly { readonly code: string; readonly name: string }[];
  readonly today: string;
}) {
  const [state, action] = useActionState(createReport, initialActionState);
  return (
    <form action={action} className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Field label={copy.create.product}>
          <select name="product_code" defaultValue={state.fields?.product_code} required className={inputClass}>
            {products.map((product) => (
              <option key={product.code} value={product.code}>
                {product.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label={copy.create.type}>
          <select name="report_type" defaultValue={state.fields?.report_type ?? 'pbrer'} className={inputClass}>
            <option value="pbrer">PBRER</option>
            <option value="pader">PADER</option>
          </select>
        </Field>
        <Field label={copy.create.intervalStart}>
          <input type="date" name="interval_start" defaultValue={state.fields?.interval_start} required max={today} className={inputClass} />
        </Field>
        <Field label={copy.create.dataLockPoint}>
          <input type="date" name="data_lock_point" required defaultValue={state.fields?.data_lock_point ?? today} max={today} className={inputClass} />
        </Field>
      </div>
      <FormNotice state={state} />
      <div>
        <SubmitButton pending="Creating…">{copy.create.submit}</SubmitButton>
      </div>
    </form>
  );
}

type SectionProps = { readonly reportNumber: string; readonly sectionKey: string; readonly version: number };

function Hidden({ reportNumber, sectionKey, version }: SectionProps) {
  return (
    <>
      <input type="hidden" name="report_number" value={reportNumber} />
      <input type="hidden" name="key" value={sectionKey} />
      <input type="hidden" name="expected_version" value={version} />
    </>
  );
}

export function AcceptSection(props: SectionProps) {
  const [state, action] = useActionState(updateSection, initialActionState);
  return (
    <form action={action} className="flex flex-col gap-2">
      <Hidden {...props} />
      <input type="hidden" name="action" value="accept" />
      <SubmitButton pending="Accepting…">{copy.workspace.accept}</SubmitButton>
      <FormNotice state={state} revision={props.version} />
    </form>
  );
}

export function SectionEditor({ text, cancelHref, ...props }: SectionProps & { readonly text: string; readonly cancelHref: string }) {
  const [state, action] = useActionState(updateSection, initialActionState);
  return (
    <form action={action} className="flex flex-col gap-4">
      <Hidden {...props} />
      <input type="hidden" name="action" value="edit" />
      <Field label={copy.workspace.text}>
        <textarea name="text" defaultValue={state.fields?.text ?? text} required maxLength={12000} rows={12} className={cn(inputClass, 'py-2.5 leading-[1.65]')} />
      </Field>
      <Field label={copy.workspace.reason}>
        <input type="text" name="reason" defaultValue={state.fields?.reason} maxLength={500} className={inputClass} />
      </Field>
      <FormNotice state={state} revision={props.version} />
      <div className="flex flex-wrap gap-2">
        <SubmitButton pending="Saving…">{copy.workspace.save}</SubmitButton>
        <Link href={cancelHref} className="inline-flex min-h-[44px] items-center rounded-control px-4 text-[14px] font-medium text-secondary hover:bg-raised">
          {copy.workspace.cancel}
        </Link>
      </div>
    </form>
  );
}

/** QPPV sign-off: the meaning is shown and recorded; the password is checked again by Vyom OS. */
export function SignOffForm({
  reportNumber,
  version,
  meaning,
}: {
  readonly reportNumber: string;
  readonly version: number;
  readonly meaning: string;
}) {
  const [state, action] = useActionState(signOffReport, initialActionState);
  const s = copy.workspace.signoff;
  return (
    <form action={action} className="flex flex-col gap-3">
      <input type="hidden" name="report_number" value={reportNumber} />
      <input type="hidden" name="version" value={version} />
      <input type="hidden" name="meaning" value={meaning} />
      <p className="m-0 rounded-control border border-amber-line bg-amber-soft px-3 py-2 text-[13px] leading-[1.45] text-amber">{meaning}</p>
      <Field label={s.password} hint={s.passwordHint}>
        <input type="password" name="password" required autoComplete="current-password" className={inputClass} />
      </Field>
      <FormNotice state={state} />
      <SubmitButton pending="Signing…">{s.submit}</SubmitButton>
    </form>
  );
}
