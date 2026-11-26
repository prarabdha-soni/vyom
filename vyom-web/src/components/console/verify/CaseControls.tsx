'use client';

/**
 * Case mutations: field edits, causality, narrative, workflow transitions
 * and E2B export. Each submits to a server action; Vyom OS re-checks role,
 * version and status before anything changes.
 */

import Link from 'next/link';
import { useActionState, useState } from 'react';
import { fieldOptions, humanise, verifyCopy } from '@/content/console';
import { cn } from '@/lib/cn';
import { draftNarrative, exportCase, saveCase, transitionCase } from '@/lib/console/actions';
import type { CasePayload } from '@/lib/gateway/types';
import { Field, FormNotice, SubmitButton, initialActionState, inputClass } from '../forms';

const copy = verifyCopy.workspace;
const fields = copy.fields;

type Common = { readonly caseNumber: string; readonly version: number };
/** Changes whenever the case does (version, status, exports); clears notices from earlier actions. */
type Revision = { readonly revision?: string };

function Hidden({ caseNumber, version }: Common) {
  return (
    <>
      <input type="hidden" name="case_number" value={caseNumber} />
      <input type="hidden" name="expected_version" value={version} />
    </>
  );
}

const nullable = (value: string) => (value.trim() === '' ? null : value);

function Select({
  value,
  options,
  onChange,
  label,
  disabled,
}: {
  readonly value: string | null;
  readonly options: readonly string[];
  readonly onChange: (value: string | null) => void;
  readonly label: string;
  readonly disabled?: boolean;
}) {
  return (
    <Field label={label}>
      <select value={value ?? ''} disabled={disabled} onChange={(event) => onChange(nullable(event.target.value))} className={inputClass}>
        <option value="">—</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {humanise(option)}
          </option>
        ))}
      </select>
    </Field>
  );
}

function Text({
  value,
  onChange,
  label,
  type = 'text',
}: {
  readonly value: string | number | null;
  readonly onChange: (value: string | null) => void;
  readonly label: string;
  readonly type?: 'text' | 'date' | 'number';
}) {
  return (
    <Field label={label}>
      <input type={type} value={value ?? ''} onChange={(event) => onChange(nullable(event.target.value))} className={inputClass} />
    </Field>
  );
}

function EditorGroup({ title, children }: { readonly title: string; readonly children: React.ReactNode }) {
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-3 rounded-nested border border-line p-4">
      <legend className="px-1 text-[13px] font-semibold text-primary">{title}</legend>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">{children}</div>
    </fieldset>
  );
}

/** Edits the structured fields. Causality is open only to the safety physician. */
export function CaseEditor({
  caseNumber,
  version,
  payload: initial,
  canAssessCausality,
  cancelHref,
}: Common & { readonly payload: CasePayload; readonly canAssessCausality: boolean; readonly cancelHref: string }) {
  const [state, action] = useActionState(saveCase, initialActionState);
  const [payload, setPayload] = useState<CasePayload>(() => structuredClone(initial));
  const update = (change: (draft: CasePayload) => void) =>
    setPayload((current) => {
      const draft = structuredClone(current);
      change(draft);
      return draft;
    });

  return (
    <form action={action} className="flex flex-col gap-4">
      <Hidden caseNumber={caseNumber} version={version} />
      <input type="hidden" name="payload" value={JSON.stringify(payload)} />
      <input type="hidden" name="return_tab" value="case" />

      <EditorGroup title={copy.patient}>
        <Text label={fields.initials} value={payload.patient.initials} onChange={(v) => update((d) => void (d.patient.initials = v))} />
        <Text
          label={`${fields.age} (value)`}
          type="number"
          value={payload.patient.age_value}
          onChange={(v) => update((d) => void (d.patient.age_value = v === null ? null : Number(v)))}
        />
        <Select label={`${fields.age} (unit)`} value={payload.patient.age_unit} options={fieldOptions.ageUnit} onChange={(v) => update((d) => void (d.patient.age_unit = v))} />
        <Select label={fields.sex} value={payload.patient.sex} options={fieldOptions.sex} onChange={(v) => update((d) => void (d.patient.sex = v))} />
        <Text
          label={fields.weight}
          type="number"
          value={payload.patient.weight_kg}
          onChange={(v) => update((d) => void (d.patient.weight_kg = v === null ? null : Number(v)))}
        />
      </EditorGroup>

      <EditorGroup title={copy.reporter}>
        <Select
          label={fields.qualification}
          value={payload.reporter.qualification}
          options={fieldOptions.qualification}
          onChange={(v) => update((d) => void (d.reporter.qualification = v))}
        />
        <Text label={fields.country} value={payload.reporter.country} onChange={(v) => update((d) => void (d.reporter.country = v))} />
      </EditorGroup>

      {payload.products.map((product, index) => (
        <EditorGroup key={`p${index}`} title={`${copy.products} · ${product.name ?? index + 1}`}>
          <Text label={fields.dose} value={product.dose} onChange={(v) => update((d) => void (d.products[index]!.dose = v))} />
          <Text label={fields.route} value={product.route} onChange={(v) => update((d) => void (d.products[index]!.route = v))} />
          <Text label={fields.indication} value={product.indication} onChange={(v) => update((d) => void (d.products[index]!.indication = v))} />
          <Text label="Start date" type="date" value={product.start_date} onChange={(v) => update((d) => void (d.products[index]!.start_date = v))} />
          <Text label="Stop date" type="date" value={product.stop_date} onChange={(v) => update((d) => void (d.products[index]!.stop_date = v))} />
          <Select
            label={fields.action}
            value={product.action_taken}
            options={fieldOptions.actionTaken}
            onChange={(v) => update((d) => void (d.products[index]!.action_taken = v))}
          />
        </EditorGroup>
      ))}

      {payload.reactions.map((reaction, index) => (
        <EditorGroup key={`r${index}`} title={`${copy.reactions} · ${reaction.verbatim ?? index + 1}`}>
          <Text label={fields.verbatim} value={reaction.verbatim} onChange={(v) => update((d) => void (d.reactions[index]!.verbatim = v))} />
          <Text label={fields.onset} type="date" value={reaction.onset_date} onChange={(v) => update((d) => void (d.reactions[index]!.onset_date = v))} />
          <Select
            label={fields.outcome}
            value={reaction.outcome}
            options={fieldOptions.outcome}
            onChange={(v) => update((d) => void (d.reactions[index]!.outcome = v))}
          />
          <fieldset className="m-0 flex flex-col gap-1.5 border-0 p-0 sm:col-span-2 xl:col-span-3">
            <legend className="mb-1.5 text-[13px] font-medium text-secondary">{fields.seriousness}</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {fieldOptions.serious.map((criterion) => (
                <label key={criterion} className="flex min-h-[28px] items-center gap-2 text-[13.5px] text-secondary">
                  <input
                    type="checkbox"
                    checked={reaction.serious_criteria.includes(criterion)}
                    onChange={(event) =>
                      update((d) => {
                        const list = d.reactions[index]!.serious_criteria.filter((item) => item !== criterion);
                        d.reactions[index]!.serious_criteria = event.target.checked ? [...list, criterion] : list;
                      })
                    }
                    className="size-4 accent-[var(--color-ink)]"
                  />
                  {humanise(criterion)}
                </label>
              ))}
            </div>
          </fieldset>
          <Select
            label={`${fields.causality}${canAssessCausality ? '' : ' · physician only'}`}
            value={reaction.causality?.category ?? null}
            options={fieldOptions.causality}
            disabled={!canAssessCausality}
            onChange={(v) =>
              update((d) => {
                const current = d.reactions[index]!;
                current.causality = { method: 'WHO-UMC', comment: null, assessed_by: null, assessed_at: null, ...current.causality, category: v };
              })
            }
          />
          {canAssessCausality ? (
            <Field label={copy.causality.comment} className="sm:col-span-1 xl:col-span-2">
              <input
                type="text"
                value={reaction.causality?.comment ?? ''}
                onChange={(event) =>
                  update((d) => {
                    const current = d.reactions[index]!;
                    current.causality = {
                      method: 'WHO-UMC',
                      category: null,
                      assessed_by: null,
                      assessed_at: null,
                      ...current.causality,
                      comment: nullable(event.target.value),
                    };
                  })
                }
                className={inputClass}
              />
            </Field>
          ) : null}
        </EditorGroup>
      ))}

      <Field label={copy.edit.reason} hint={copy.edit.reasonHint}>
        <input type="text" name="reason" defaultValue={state.fields?.reason} required maxLength={500} className={inputClass} />
      </Field>
      <FormNotice state={state} />
      <div className="flex flex-wrap gap-2">
        <SubmitButton pending="Saving…">{copy.edit.save}</SubmitButton>
        <Link href={cancelHref} className="inline-flex min-h-[44px] items-center rounded-control px-4 text-[14px] font-medium text-secondary hover:bg-raised">
          {copy.edit.cancel}
        </Link>
      </div>
    </form>
  );
}

/** Narrative text editor; a changed narrative is marked as reviewed by a person. */
export function NarrativeEditor({
  caseNumber,
  version,
  payload,
  cancelHref,
}: Common & { readonly payload: CasePayload; readonly cancelHref: string }) {
  const [state, action] = useActionState(saveCase, initialActionState);
  const [text, setText] = useState(payload.narrative?.text ?? '');
  const next: CasePayload = { ...payload, narrative: { status: 'edited', citations: [], ...payload.narrative, text } };
  return (
    <form action={action} className="flex flex-col gap-4">
      <Hidden caseNumber={caseNumber} version={version} />
      <input type="hidden" name="payload" value={JSON.stringify(next)} />
      <input type="hidden" name="return_tab" value="narrative" />
      <Field label={copy.narrative.heading}>
        <textarea value={text} onChange={(event) => setText(event.target.value)} rows={12} className={cn(inputClass, 'py-2.5 leading-[1.6]')} />
      </Field>
      <Field label={copy.edit.reason} hint={copy.edit.reasonHint}>
        <input type="text" name="reason" defaultValue={state.fields?.reason} required maxLength={500} className={inputClass} />
      </Field>
      <FormNotice state={state} />
      <div className="flex flex-wrap gap-2">
        <SubmitButton pending="Saving…">{copy.narrative.save}</SubmitButton>
        <Link href={cancelHref} className="inline-flex min-h-[44px] items-center rounded-control px-4 text-[14px] font-medium text-secondary hover:bg-raised">
          {copy.edit.cancel}
        </Link>
      </div>
    </form>
  );
}

/** Marks an unreviewed narrative draft as reviewed, without changing its words. */
export function ConfirmNarrative({ caseNumber, version, revision, payload }: Common & Revision & { readonly payload: CasePayload }) {
  const [state, action] = useActionState(saveCase, initialActionState);
  const next: CasePayload = {
    ...payload,
    narrative: { text: payload.narrative?.text ?? '', citations: payload.narrative?.citations ?? [], status: 'edited' },
  };
  return (
    <form action={action} className="flex flex-col gap-2">
      <Hidden caseNumber={caseNumber} version={version} />
      <input type="hidden" name="payload" value={JSON.stringify(next)} />
      <input type="hidden" name="return_tab" value="narrative" />
      <input type="hidden" name="reason" value="Narrative checked against the source and confirmed" />
      <SubmitButton variant="panel" pending="Confirming…">
        {copy.narrative.confirm}
      </SubmitButton>
      <FormNotice state={state} revision={revision} />
    </form>
  );
}

export function DraftNarrative({ caseNumber, version, revision, redraft }: Common & Revision & { readonly redraft: boolean }) {
  const [state, action] = useActionState(draftNarrative, initialActionState);
  return (
    <form action={action} className="flex flex-col gap-2">
      <Hidden caseNumber={caseNumber} version={version} />
      <SubmitButton variant={redraft ? 'panel' : 'panelPrimary'} pending="Drafting…">
        {redraft ? copy.narrative.redraft : copy.narrative.draft}
      </SubmitButton>
      <FormNotice state={state} revision={revision} />
    </form>
  );
}

export function ExportE2B({ caseNumber, revision }: { readonly caseNumber: string } & Revision) {
  const [state, action] = useActionState(exportCase, initialActionState);
  return (
    <form action={action} className="flex flex-col gap-2">
      <input type="hidden" name="case_number" value={caseNumber} />
      <SubmitButton variant="panel" pending="Exporting…">
        {copy.exports.create}
      </SubmitButton>
      <FormNotice state={state} revision={revision} />
    </form>
  );
}

export type TransitionOption = { readonly action: string; readonly label: string; readonly needsReason: boolean };

/** One workflow step at a time: pick it, give a reason where one is required, confirm. */
export function Transitions({
  caseNumber,
  version,
  revision,
  options,
}: Common & Revision & { readonly options: readonly TransitionOption[] }) {
  const [state, action] = useActionState(transitionCase, initialActionState);
  const [selected, setSelected] = useState<string | null>(null);
  const choice = options.find((option) => option.action === selected);
  const t = copy.transitions;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option.action}
            type="button"
            aria-pressed={selected === option.action}
            onClick={() => setSelected(selected === option.action ? null : option.action)}
            className={cn(
              'min-h-[40px] cursor-pointer rounded-control border px-3 text-[13.5px] font-medium transition-colors',
              selected === option.action ? 'border-ink bg-ink text-on-ink' : 'border-button bg-surface text-primary hover:bg-raised',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
      {choice ? (
        <form action={action} className="flex flex-col gap-3 rounded-nested border border-line bg-panel-header p-3">
          <Hidden caseNumber={caseNumber} version={version} />
          <input type="hidden" name="action" value={choice.action} />
          {choice.action === 'approve' ? (
            <p className="m-0 rounded-control border border-amber-line bg-amber-soft px-3 py-2 text-[13px] leading-[1.45] text-amber">
              {t.approveMeaning}
            </p>
          ) : null}
          {choice.action === 'mark_duplicate' ? (
            <Field label={t.duplicateOf}>
              <input type="text" name="duplicate_of" defaultValue={state.fields?.duplicate_of} required placeholder="VY-CASE-0000" className={cn(inputClass, 'font-mono')} />
            </Field>
          ) : null}
          {choice.needsReason || choice.action === 'approve' ? (
            <Field label={t.reason}>
              <input type="text" name="reason" defaultValue={state.fields?.reason} required={choice.needsReason} maxLength={500} className={inputClass} />
            </Field>
          ) : null}
          <SubmitButton pending="Working…">{choice.label}</SubmitButton>
        </form>
      ) : null}
      <FormNotice state={state} revision={revision} />
    </div>
  );
}
