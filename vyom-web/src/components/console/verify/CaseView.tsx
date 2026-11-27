/**
 * Read-only case document: every field beside the source words it came
 * from. Verified evidence is green; anything without a quote says so.
 */

import type { ReactNode } from 'react';
import { humanise, verifyCopy } from '@/content/console';
import { CheckIcon, DashedCircleIcon, QuoteIcon } from '@/components/icons';
import { Chip } from '@/components/ui';
import { formatDate, formatDateTime, shortEmail } from '@/lib/console/format';
import type { CaseDetail, Evidence } from '@/lib/gateway/types';
import { ClockChip, KeyValues, Panel } from '../ui';

const copy = verifyCopy.workspace;
const fields = copy.fields;

function Value({ children }: { readonly children: ReactNode }) {
  return children === null || children === undefined || children === '' ? (
    <span className="text-meta">{copy.notReported}</span>
  ) : (
    <>{children}</>
  );
}

export function EvidenceQuote({ evidence }: { readonly evidence: Evidence | undefined }) {
  if (!evidence) {
    return <p className="m-0 font-mono text-[11.5px] text-meta">{copy.noEvidence}</p>;
  }
  const verified = evidence.status === 'verified';
  return (
    <figure className={`m-0 flex items-start gap-2.5 rounded-control border px-3 py-2 ${verified ? 'border-green-line bg-green-soft' : 'border-dashed border-dash bg-raised'}`}>
      <QuoteIcon className={`mt-0.5 shrink-0 ${verified ? 'text-green' : 'text-meta'}`} />
      <blockquote className="m-0 min-w-0 flex-1 text-[13.5px] leading-[1.5] text-secondary">{evidence.quote}</blockquote>
      <figcaption>
        <Chip tone={verified ? 'green' : 'dashed'} size="xs">
          {verified ? copy.verified : copy.unverified}
        </Chip>
      </figcaption>
    </figure>
  );
}

function Block({
  title,
  evidence,
  showEvidence = true,
  children,
}: {
  readonly title: string;
  readonly evidence?: Evidence;
  readonly showEvidence?: boolean;
  readonly children: ReactNode;
}) {
  return (
    <Panel title={title} headingLevel={3}>
      <div className="flex flex-col gap-4">
        {children}
        {showEvidence ? (
          <div className="flex flex-col gap-1.5">
            <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.evidence}</span>
            <EvidenceQuote evidence={evidence} />
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

export function CaseView({ detail }: { readonly detail: CaseDetail }) {
  const { payload, assessment } = detail;
  const { patient, reporter } = payload;
  const evidence = payload.evidence ?? {};

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
        <Block title={copy.patient} evidence={evidence.patient}>
          <KeyValues
            columns={3}
            items={[
              { label: fields.initials, value: <Value>{patient.initials}</Value> },
              {
                label: fields.age,
                value: <Value>{patient.age_value !== null ? `${patient.age_value} ${patient.age_unit ?? ''}` : null}</Value>,
              },
              { label: fields.ageGroup, value: <Value>{humanise(patient.age_group)}</Value> },
              { label: fields.sex, value: <Value>{humanise(patient.sex)}</Value> },
              { label: fields.weight, value: <Value>{patient.weight_kg}</Value> },
              { label: fields.pregnant, value: <Value>{patient.pregnant === null ? null : patient.pregnant ? 'Yes' : 'No'}</Value> },
            ]}
          />
        </Block>
        <Block title={copy.reporter} evidence={evidence.reporter}>
          <KeyValues
            items={[
              { label: fields.qualification, value: <Value>{humanise(reporter.qualification)}</Value> },
              { label: fields.country, value: <Value>{reporter.country}</Value> },
              {
                label: fields.identifiable,
                value: <Value>{reporter.identifiable === null ? null : reporter.identifiable ? 'Yes' : 'No'}</Value>,
              },
              { label: 'Description', value: <Value>{reporter.description}</Value> },
            ]}
          />
        </Block>
      </div>

      {payload.products.map((product, index) => (
        <Block key={`product-${index}`} title={`${copy.products} · ${product.name ?? product.product_code ?? index + 1}`} evidence={evidence[`products.${index}`]}>
          <div className="flex flex-wrap gap-1.5">
            {product.role ? (
              <Chip tone="muted" size="xs">
                {product.role.toUpperCase()}
              </Chip>
            ) : null}
            {product.product_code ? (
              <Chip tone="default" size="xs">
                {product.product_code}
              </Chip>
            ) : null}
          </div>
          <KeyValues
            columns={3}
            items={[
              { label: fields.dose, value: <Value>{product.dose}</Value> },
              { label: fields.route, value: <Value>{humanise(product.route)}</Value> },
              { label: fields.indication, value: <Value>{product.indication}</Value> },
              {
                label: fields.dates,
                value: <Value>{product.start_date ? `${formatDate(product.start_date)} → ${product.stop_date ? formatDate(product.stop_date) : 'ongoing'}` : null}</Value>,
              },
              { label: fields.action, value: <Value>{humanise(product.action_taken)}</Value> },
            ]}
          />
        </Block>
      ))}

      {payload.reactions.map((reaction, index) => {
        const expectedness = assessment.expectedness.find((item) => item.index === index);
        const causality = reaction.causality;
        return (
          <Block key={`reaction-${index}`} title={`${copy.reactions} · ${reaction.verbatim ?? index + 1}`} evidence={evidence[`reactions.${index}`]}>
            <KeyValues
              columns={3}
              items={[
                { label: fields.onset, value: <Value>{reaction.onset_date ? formatDate(reaction.onset_date) : null}</Value> },
                { label: fields.outcome, value: <Value>{humanise(reaction.outcome)}</Value> },
                {
                  label: fields.seriousness,
                  value: reaction.serious_criteria.length ? (
                    <span className="flex flex-wrap gap-1">
                      {reaction.serious_criteria.map((criterion) => (
                        <Chip key={criterion} tone="default" size="xs">
                          {humanise(criterion).toUpperCase()}
                        </Chip>
                      ))}
                    </span>
                  ) : (
                    verifyCopy.nonSerious
                  ),
                },
                {
                  label: fields.coding,
                  value: reaction.coding ? (
                    <span className="flex flex-col gap-1">
                      <span>{reaction.coding.pt ?? reaction.coding.soc ?? '—'}</span>
                      {!detail.terminology.licensed ? (
                        <span className="text-[12px] text-meta">{copy.codingUnlicensed}</span>
                      ) : null}
                      <Chip tone={reaction.coding.status === 'confirmed' ? 'green' : 'muted'} size="xs" className="w-fit">
                        {reaction.coding.status.toUpperCase()}
                      </Chip>
                    </span>
                  ) : (
                    <Value>{null}</Value>
                  ),
                },
                {
                  label: fields.expectedness,
                  value: expectedness ? (
                    <span className="flex flex-col gap-0.5">
                      <span>{expectedness.expected === null ? '—' : expectedness.expected ? copy.expected : copy.unexpected}</span>
                      <span className="text-[12px] text-meta">{expectedness.basis}</span>
                    </span>
                  ) : (
                    '—'
                  ),
                },
                {
                  label: fields.causality,
                  value: causality?.category ? (
                    <span className="flex flex-col gap-1">
                      <Chip tone="amber" size="xs" className="w-fit">
                        {causality.category.toUpperCase()}
                      </Chip>
                      {causality.comment ? <span className="text-[13px] text-secondary">{causality.comment}</span> : null}
                      <span className="text-[12px] text-meta">
                        {verifyCopy.workspace.causality.by} {shortEmail(causality.assessed_by)} · {formatDateTime(causality.assessed_at)}
                      </span>
                    </span>
                  ) : (
                    <span className="text-meta">{verifyCopy.workspace.causality.none}</span>
                  ),
                },
              ]}
            />
          </Block>
        );
      })}

      <Block title={copy.special} showEvidence={false}>
        <KeyValues
          columns={3}
          items={[
            {
              label: copy.special,
              value: payload.special_situations.length ? (
                <span className="flex flex-wrap gap-1">
                  {payload.special_situations.map((item) => (
                    <Chip key={item.kind} tone="muted" size="xs">
                      {humanise(item.kind).toUpperCase()}
                    </Chip>
                  ))}
                </span>
              ) : (
                <span className="text-meta">None</span>
              ),
            },
            {
              label: copy.history,
              value: payload.medical_history.length ? payload.medical_history.join('; ') : <span className="text-meta">None reported</span>,
            },
            {
              label: copy.challenge,
              value: `${humanise(payload.dechallenge) || '—'} · ${humanise(payload.rechallenge) || '—'}`,
            },
          ]}
        />
      </Block>
    </div>
  );
}

/** One labelled result in the rules panel. */
function Row({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5 border-b border-hairline py-3 first:pt-0 last:border-b-0 last:pb-0">
      <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{label}</span>
      <div className="text-[13.5px] leading-[1.45] text-primary">{children}</div>
    </div>
  );
}

/** The deterministic rules applied to the current version. */
export function RulesPanel({ detail }: { readonly detail: CaseDetail }) {
  const { assessment } = detail;
  const rules = copy.rules;
  return (
    <Panel title={rules.heading} lead={rules.engine(assessment.rules_version)}>
      <div className="flex flex-col">
        <Row label={rules.validity}>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {Object.entries(assessment.validity.criteria).map(([key, met]) => (
              <li key={key} className="flex items-center gap-2">
                {met ? <CheckIcon size={15} className="text-green" /> : <DashedCircleIcon size={15} className="text-meta" />}
                <span className={met ? 'text-primary' : 'text-meta'}>{rules.criteria[key] ?? humanise(key)}</span>
                <span className="sr-only">{met ? 'met' : 'missing'}</span>
              </li>
            ))}
          </ul>
        </Row>
        <Row label={rules.seriousness}>
          {assessment.seriousness.serious ? (
            <span className="flex flex-wrap gap-1">
              {assessment.seriousness.criteria.map((criterion) => (
                <Chip key={criterion} tone="default" size="xs">
                  {humanise(criterion).toUpperCase()}
                </Chip>
              ))}
            </span>
          ) : (
            verifyCopy.nonSerious
          )}
        </Row>
        <Row label={rules.expedited}>{assessment.expedited_candidate ? rules.expeditedYes : rules.expeditedNo}</Row>
        <Row label={rules.clock}>
          <span className="flex flex-wrap items-center gap-2">
            <ClockChip clock={assessment.clock} />
            {assessment.clock.due_date && assessment.clock.status !== 'stopped' ? (
              <span className="font-mono text-[12px] text-meta">
                {rules.dueOn} {formatDate(assessment.clock.due_date)}
              </span>
            ) : null}
          </span>
        </Row>
        <Row label={rules.causality}>{assessment.causality_complete ? rules.causalityDone : rules.causalityMissing}</Row>
        <Row label={rules.followUp}>
          {assessment.follow_up.required ? (
            <ul className="m-0 list-disc pl-4">
              {assessment.follow_up.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            rules.followUpNone
          )}
        </Row>
        {assessment.reference ? (
          <Row label={rules.reference}>
            {assessment.reference.product} · {assessment.reference.rsi_version ?? '—'}
          </Row>
        ) : null}
      </div>
    </Panel>
  );
}
