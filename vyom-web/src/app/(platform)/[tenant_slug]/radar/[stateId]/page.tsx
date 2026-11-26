import type { Metadata } from 'next';
import Link from 'next/link';
import { humanise, radarCopy } from '@/content/console';
import { Highlighted } from '@/components/console/Highlighted';
import { DecisionForm, ReviewKeys } from '@/components/console/radar/RadarClient';
import {
  ActivityFeed,
  BandChip,
  EngineChip,
  KeyValues,
  LoadFailed,
  OutcomeChip,
  PageBody,
  PageHeader,
  Panel,
} from '@/components/console/ui';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';
import { Chip, ProgressBar } from '@/components/ui';
import { getWorkspace, loadLiterature, loadLiteratureItem } from '@/lib/console/data';
import { formatDate, formatDateTime, formatPercent, shortEmail } from '@/lib/console/format';
import type { LiteratureDetail } from '@/lib/gateway/types';

export async function generateMetadata({ params }: PageProps<'/[tenant_slug]/radar/[stateId]'>): Promise<Metadata> {
  const { stateId } = await params;
  return { title: `Article ${stateId}` };
}

/** Suggest the outcome the screen points to; the reviewer still decides. */
function suggestion(detail: LiteratureDetail): string | null {
  const band = detail.decision?.confidence_band ?? '';
  if (band.startsWith('RED')) return 'valid_icsr';
  if (band.startsWith('GREEN')) return 'not_relevant';
  return null;
}

/** Earlier, non-final decisions on the article (an escalation and its reason). */
function OutcomeTrail({ outcomes }: { readonly outcomes: LiteratureDetail['outcomes'] }) {
  if (!outcomes.length) return null;
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {outcomes.map((outcome) => (
        <li key={outcome.created_at} className="rounded-control border border-amber-line bg-amber-soft px-3 py-2 text-[13px] text-secondary">
          <OutcomeChip outcome={outcome.outcome} /> {shortEmail(outcome.reviewer_email)} · {formatDateTime(outcome.created_at)}
          {outcome.reason ? <span className="mt-1 block">{outcome.reason}</span> : null}
        </li>
      ))}
    </ul>
  );
}

export default async function LiteratureReviewPage({ params }: PageProps<'/[tenant_slug]/radar/[stateId]'>) {
  const { tenant_slug: slug, stateId } = await params;
  const workspace = await getWorkspace();
  const result = await loadLiteratureItem(stateId);
  const base = `/${slug}/radar/`;
  const crumbs = [
    { label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` },
    { label: radarCopy.title, href: base },
  ];

  if (!result.ok) {
    return (
      <>
        <PageHeader crumbs={crumbs} title={radarCopy.title} />
        <PageBody>
          <LoadFailed error={result.error} />
        </PageBody>
      </>
    );
  }

  const detail = result.data;
  const copy = radarCopy.review;

  // Neighbours in the open queue, or in the full list once this article is decided.
  const open = await loadLiterature('open');
  let order = open.ok ? open.data.items.map((item) => item.state_id) : [];
  if (!order.includes(detail.state_id)) {
    const all = await loadLiterature('all');
    order = all.ok ? all.data.items.map((item) => item.state_id) : [];
  }
  const index = order.indexOf(detail.state_id);
  const previousId = index > 0 ? order[index - 1] : undefined;
  const nextId = index >= 0 && index < order.length - 1 ? order[index + 1] : undefined;
  const previous = previousId ? `${base}${previousId}/` : null;
  const next = nextId ? `${base}${nextId}/` : null;
  const finalOutcome = detail.final_outcome;

  return (
    <>
      <ReviewKeys previous={previous} next={next} />
      <PageHeader
        crumbs={[...crumbs, { label: detail.reference }]}
        title={<span className="font-mono text-[22px] tracking-[-0.01em] sm:text-[24px]">{detail.reference}</span>}
        meta={
          <>
            <BandChip band={detail.decision?.confidence_band ?? null} />
            {finalOutcome ? <OutcomeChip outcome={finalOutcome.outcome} /> : null}
            {detail.is_sample ? (
              <Chip tone="dashed" size="sm">
                {copy.sampleArticle}
              </Chip>
            ) : null}
          </>
        }
        actions={
          <nav aria-label="Queue" className="flex items-center gap-2">
            {[
              { href: previous, label: copy.previous, Icon: ChevronLeftIcon, key: 'K' },
              { href: next, label: copy.next, Icon: ChevronRightIcon, key: 'J' },
            ].map(({ href, label, Icon, key }) =>
              href ? (
                <Link
                  key={key}
                  href={href}
                  aria-label={label}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-control border border-button bg-surface px-3 text-[13px] font-medium text-primary hover:bg-raised"
                >
                  {key === 'K' ? <Icon /> : null}
                  <span className="font-mono text-[11px] text-meta">{key}</span>
                  {key === 'J' ? <Icon /> : null}
                </Link>
              ) : (
                <span
                  key={key}
                  aria-hidden="true"
                  className="flex min-h-[40px] items-center gap-1.5 rounded-control border border-hairline px-3 text-dash"
                >
                  {key === 'K' ? <Icon /> : null}
                  <span className="font-mono text-[11px]">{key}</span>
                  {key === 'J' ? <Icon /> : null}
                </span>
              ),
            )}
          </nav>
        }
      />
      <PageBody>
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
          <div className="flex min-w-0 flex-col gap-5 xl:col-span-7">
            <Panel title={copy.article}>
              <article className="flex flex-col gap-4">
                <h2 className="m-0 text-[20px] leading-[1.35] font-semibold tracking-[-0.015em] text-primary">
                  <Highlighted text={detail.title} highlights={detail.highlights.title} />
                </h2>
                <p className="m-0 text-[13.5px] leading-[1.5] text-meta">
                  {detail.authors.join(', ')}
                  {detail.authors.length ? ' · ' : ''}
                  {detail.journal ?? '—'} · {formatDate(detail.pub_date)}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.products.map((code) => (
                    <Chip key={code} tone="muted" size="xs">
                      {code}
                    </Chip>
                  ))}
                  {detail.pmid ? (
                    <Chip tone="default" size="xs">
                      PMID {detail.pmid}
                    </Chip>
                  ) : null}
                  {detail.doi ? (
                    <Chip tone="default" size="xs">
                      DOI {detail.doi}
                    </Chip>
                  ) : null}
                </div>
                <div className="flex flex-col gap-2">
                  <h3 className="m-0 font-mono text-[11px] font-medium tracking-[0.08em] text-meta uppercase">{copy.abstract}</h3>
                  <p className="m-0 text-[15px] leading-[1.7] whitespace-pre-line text-secondary">
                    {detail.abstract ? <Highlighted text={detail.abstract} highlights={detail.highlights.abstract} /> : copy.noAbstract}
                  </p>
                </div>
                <p className="m-0 font-mono text-[11px] leading-[1.5] text-meta">{copy.highlightNote(detail.highlights.method)}</p>
                {detail.citation ? (
                  <div className="flex flex-col gap-1 border-t border-hairline pt-3">
                    <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.citation}</span>
                    <p className="m-0 text-[13px] leading-[1.5] text-secondary">{detail.citation}</p>
                  </div>
                ) : null}
              </article>
            </Panel>
            <Panel title={copy.history}>
              <ActivityFeed rows={detail.history} tenantSlug={slug} empty="—" />
            </Panel>
          </div>

          <div className="flex min-w-0 flex-col gap-5 xl:col-span-5">
            <Panel
              title={copy.screening}
              action={<EngineChip isAi={detail.is_ai} model={detail.decision?.model_id} />}
            >
              <div className="flex flex-col gap-5">
                {detail.summary ? (
                  <KeyValues
                    items={[
                      { label: copy.band, value: <BandChip band={detail.decision?.confidence_band ?? null} /> },
                      {
                        label: 'Criteria met',
                        value: detail.summary.criteria_met === null ? '—' : radarCopy.criteriaMet(detail.summary.criteria_met),
                      },
                      { label: copy.seriousness, value: formatPercent(detail.summary.p_serious) },
                      { label: copy.studyDesign, value: humanise(detail.summary.study_design?.toLowerCase()) || '—' },
                    ]}
                  />
                ) : null}
                <div className="flex flex-col gap-1">
                  <h3 className="m-0 mb-1 font-mono text-[11px] font-medium tracking-[0.08em] text-meta uppercase">{copy.questions}</h3>
                  <ul className="m-0 flex list-none flex-col p-0">
                    {detail.questions.map((question) => {
                      const answer = question.answer;
                      const value = answer?.answer ?? answer?.choice ?? (answer?.score !== undefined ? String(answer.score) : '—');
                      return (
                        <li key={question.key} className="flex flex-col gap-1.5 border-b border-hairline py-2.5 last:border-b-0">
                          <span className="text-[13.5px] leading-[1.45] text-secondary">{question.prompt}</span>
                          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                            <span className="min-w-[72px] font-mono text-[12px] font-medium break-all text-primary">{value}</span>
                            {answer?.probability !== undefined ? (
                              <span className="flex min-w-[160px] flex-1 items-center gap-3">
                                <ProgressBar width={answer.probability * 100} tone={detail.is_ai ? 'accent' : 'ink'} />
                                <span className="w-[40px] shrink-0 text-right font-mono text-[11.5px] text-meta">
                                  {formatPercent(answer.probability)}
                                </span>
                              </span>
                            ) : null}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </div>
            </Panel>

            <Panel title={finalOutcome ? copy.decided : copy.decision}>
              {finalOutcome ? (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <OutcomeChip outcome={finalOutcome.outcome} />
                    <span className="text-[13px] text-meta">
                      {shortEmail(finalOutcome.reviewer_email)} · {formatDateTime(finalOutcome.created_at)}
                    </span>
                  </div>
                  {finalOutcome.reason ? <p className="m-0 text-[14px] leading-[1.5] text-secondary">{finalOutcome.reason}</p> : null}
                  {finalOutcome.case_number ? (
                    <Link
                      href={`/${slug}/verify/${finalOutcome.case_number}/`}
                      className="inline-flex min-h-[40px] w-fit items-center gap-2 rounded-control border border-button px-3 text-[13.5px] font-medium text-primary hover:bg-raised"
                    >
                      {copy.openCase} <span className="font-mono">{finalOutcome.case_number}</span>
                    </Link>
                  ) : null}
                </div>
              ) : detail.can_decide && detail.decision ? (
                <div className="flex flex-col gap-4">
                  <OutcomeTrail outcomes={detail.outcomes} />
                  <DecisionForm
                    stateId={detail.state_id}
                    decisionId={detail.decision.id}
                    suggested={suggestion(detail)}
                    urgent={detail.decision.confidence_band === 'RED_ESCALATE'}
                    nextStateId={nextId ?? null}
                  />
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {detail.awaiting_physician ? <OutcomeTrail outcomes={detail.outcomes} /> : null}
                  <p className="m-0 text-[14px] text-muted">{detail.awaiting_physician ? copy.awaitingPhysician : copy.cannotDecide}</p>
                </div>
              )}
            </Panel>
          </div>
        </div>
      </PageBody>
    </>
  );
}
