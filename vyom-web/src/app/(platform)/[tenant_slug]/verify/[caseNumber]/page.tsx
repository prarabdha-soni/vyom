import type { Metadata } from 'next';
import Link from 'next/link';
import { channelLabel, verifyCopy } from '@/content/console';
import { Highlighted } from '@/components/console/Highlighted';
import { CaseView, EvidenceQuote, RulesPanel } from '@/components/console/verify/CaseView';
import {
  CaseEditor,
  ConfirmNarrative,
  DraftNarrative,
  ExportE2B,
  NarrativeEditor,
  type TransitionOption,
  Transitions,
} from '@/components/console/verify/CaseControls';
import {
  ActivityFeed,
  CaseStatusChip,
  ClockChip,
  EngineChip,
  LoadFailed,
  PageBody,
  PageHeader,
  Panel,
  SegmentedTabs,
  td,
  th,
} from '@/components/console/ui';
import { DownloadIcon, PencilIcon } from '@/components/icons';
import { ButtonLink, Chip, ScrollableTable } from '@/components/ui';
import { type Workspace, can, getWorkspace, loadCase } from '@/lib/console/data';
import { formatDateTime, shortEmail } from '@/lib/console/format';
import type { CaseDetail, Highlight } from '@/lib/gateway/types';

export async function generateMetadata({ params }: PageProps<'/[tenant_slug]/verify/[caseNumber]'>): Promise<Metadata> {
  const { caseNumber } = await params;
  return { title: decodeURIComponent(caseNumber) };
}

const TABS = ['case', 'source', 'narrative', 'history'] as const;
type Tab = (typeof TABS)[number];
const OPEN = new Set(['data_entry', 'medical_review']);
const copy = verifyCopy.workspace;

function transitionOptions(detail: CaseDetail, workspace: Workspace): TransitionOption[] {
  const status = detail.case.status;
  const { permissions } = detail;
  const approver = can(workspace, 'case.approve');
  const actions: string[] = [];
  if (status === 'data_entry' && permissions.submit && detail.assessment.validity.valid) actions.push('submit');
  if (status === 'medical_review' && permissions.approve) actions.push('approve');
  if (status === 'medical_review' && approver) actions.push('return');
  if (OPEN.has(status) && permissions.submit) {
    if (!detail.assessment.validity.valid) actions.push('close_invalid');
    actions.push('mark_duplicate');
  }
  if (!OPEN.has(status) && approver) actions.push('reopen');
  return actions.map((action) => {
    const option = copy.transitions.actions[action];
    return { action, label: option?.label ?? action, needsReason: option?.needsReason ?? true };
  });
}

export default async function CasePage({ params, searchParams }: PageProps<'/[tenant_slug]/verify/[caseNumber]'>) {
  const { tenant_slug: slug, caseNumber: rawNumber } = await params;
  const caseNumber = decodeURIComponent(rawNumber);
  const query = await searchParams;
  const tab: Tab = TABS.find((value) => value === query.tab) ?? 'case';
  const editing = query.edit === '1';
  const workspace = await getWorkspace();
  const result = await loadCase(caseNumber);
  const base = `/${slug}/verify/`;
  const here = `${base}${encodeURIComponent(caseNumber)}/`;
  const crumbs = [
    { label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` },
    { label: verifyCopy.title, href: base },
    { label: caseNumber },
  ];

  if (!result.ok) {
    return (
      <>
        <PageHeader crumbs={crumbs} title={caseNumber} />
        <PageBody>
          <LoadFailed error={result.error} />
        </PageBody>
      </>
    );
  }

  const detail = result.data;
  const { case: head, permissions } = detail;
  // Any change to the case moves this on, which clears notices left by earlier actions.
  const revision = `${detail.version.number}:${head.status}:${detail.exports.length}`;
  const narrativeRoute = workspace.me.ai.case_narrative;
  const narrativeIsAi = workspace.me.ai.is_ai && narrativeRoute?.provider !== 'demo';
  const options = transitionOptions(detail, workspace);
  const tabHref = (value: Tab) => (value === 'case' ? here : `${here}?tab=${value}`);

  return (
    <>
      <PageHeader
        crumbs={crumbs}
        title={<span className="font-mono text-[22px] tracking-[-0.01em] sm:text-[24px]">{caseNumber}</span>}
        meta={
          <>
            <CaseStatusChip status={head.status} />
            {head.serious ? (
              <Chip tone="default" size="sm">
                {verifyCopy.serious}
              </Chip>
            ) : (
              <Chip tone="muted" size="sm">
                {copy.nonSeriousChip}
              </Chip>
            )}
            {detail.assessment.expedited_candidate ? (
              <Chip tone="default" size="sm">
                {verifyCopy.expedited}
              </Chip>
            ) : null}
            <ClockChip clock={detail.assessment.clock} />
            <span className="font-mono text-[12px] text-meta">
              {copy.version(detail.version.number)} · {channelLabel[head.source_channel] ?? head.source_channel} ·{' '}
              {head.product_name ?? head.product_code}
            </span>
          </>
        }
        actions={
          tab === 'case' && permissions.edit && !editing ? (
            <ButtonLink href={`${here}?edit=1`} variant="panel">
              <PencilIcon size={16} />
              {copy.edit.open}
            </ButtonLink>
          ) : null
        }
      >
        <SegmentedTabs
          label={copy.tabsLabel}
          items={copy.tabs.map((item) => ({ label: item.label, href: tabHref(item.value), active: item.value === tab }))}
        />
      </PageHeader>

      <PageBody>
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
          <div className="flex min-w-0 flex-col gap-4 xl:col-span-8">
            {tab === 'case' ? (
              editing && permissions.edit ? (
                <Panel title={copy.edit.open}>
                  <CaseEditor
                    caseNumber={caseNumber}
                    version={detail.version.number}
                    payload={detail.payload}
                    canAssessCausality={permissions.assess_causality}
                    cancelHref={here}
                  />
                </Panel>
              ) : (
                <CaseView detail={detail} />
              )
            ) : null}

            {tab === 'source' ? <SourceView detail={detail} /> : null}

            {tab === 'narrative' ? (
              <Panel
                title={copy.narrative.heading}
                action={
                  <span className="flex flex-wrap items-center gap-2">
                    {detail.payload.narrative?.status ? (
                      <Chip
                        tone={detail.payload.narrative.status === 'edited' ? 'green' : narrativeIsAi ? 'accent' : 'muted'}
                        size="xs"
                      >
                        {copy.narrative.statusLabel[detail.payload.narrative.status] ?? detail.payload.narrative.status.toUpperCase()}
                      </Chip>
                    ) : null}
                    <EngineChip isAi={narrativeIsAi} model={narrativeRoute?.model_id} />
                  </span>
                }
              >
                {editing && permissions.edit ? (
                  <NarrativeEditor
                    caseNumber={caseNumber}
                    version={detail.version.number}
                    payload={detail.payload}
                    cancelHref={`${here}?tab=narrative`}
                  />
                ) : (
                  <div className="flex flex-col gap-5">
                    {detail.payload.narrative?.text ? (
                      <p className="m-0 text-[15px] leading-[1.75] whitespace-pre-line text-secondary">{detail.payload.narrative.text}</p>
                    ) : (
                      <p className="m-0 text-[14px] text-muted">{copy.narrative.empty}</p>
                    )}
                    {detail.payload.narrative?.citations.length ? (
                      <div className="flex flex-col gap-2">
                        <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.narrative.citations}</span>
                        {detail.payload.narrative.citations.map((quote) => (
                          <EvidenceQuote key={quote} evidence={{ quote, start: 0, end: 0, status: 'verified' }} />
                        ))}
                      </div>
                    ) : null}
                    {permissions.edit ? (
                      <div className="flex flex-wrap items-start gap-2 border-t border-hairline pt-4">
                        <DraftNarrative caseNumber={caseNumber} version={detail.version.number} revision={revision} redraft={Boolean(detail.payload.narrative?.text)} />
                        {detail.payload.narrative?.status === 'ai_draft' ? (
                          <ConfirmNarrative caseNumber={caseNumber} version={detail.version.number} revision={revision} payload={detail.payload} />
                        ) : null}
                        <ButtonLink href={`${here}?tab=narrative&edit=1`} variant="panel">
                          <PencilIcon size={16} />
                          {copy.narrative.edit}
                        </ButtonLink>
                      </div>
                    ) : null}
                  </div>
                )}
              </Panel>
            ) : null}

            {tab === 'history' ? (
              <>
                <Panel title={copy.versions} bodyClassName="p-0">
                  <ScrollableTable label={copy.versions}>
                    <table className="w-full min-w-[640px] border-collapse">
                      <thead>
                        <tr>
                          {copy.versionColumns.map((column) => (
                            <th key={column} scope="col" className={th}>
                              {column}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {detail.versions.map((version) => (
                          <tr key={version.version}>
                            <td className={`${td} font-mono text-primary`}>v{version.version}</td>
                            <td className={td}>
                              <span className="flex flex-col items-start gap-1">
                                <span>{shortEmail(version.author_email) || '—'}</span>
                                {version.author_kind === 'human' ? (
                                  <Chip tone="amber" size="xs">
                                    {copy.humanAuthor}
                                  </Chip>
                                ) : (
                                  <EngineChip isAi={version.is_ai} model={version.model_id} />
                                )}
                              </span>
                            </td>
                            <td className={td}>{version.reason ?? '—'}</td>
                            <td className={`${td} font-mono text-[12px] whitespace-nowrap text-meta`}>{formatDateTime(version.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </ScrollableTable>
                </Panel>
                <Panel title={copy.activity}>
                  <ActivityFeed rows={detail.history} tenantSlug={slug} empty="—" />
                </Panel>
              </>
            ) : null}
          </div>

          <aside aria-label={copy.checksLabel} className="flex min-w-0 flex-col gap-4 xl:col-span-4">
            <Panel title={copy.transitions.heading}>
              {options.length ? (
                <Transitions caseNumber={caseNumber} version={detail.version.number} revision={revision} options={options} />
              ) : (
                <p className="m-0 text-[13.5px] text-muted">{copy.transitions.none}</p>
              )}
            </Panel>

            <RulesPanel detail={detail} />

            {detail.duplicates.length ? (
              <Panel title={copy.duplicates.heading}>
                <ul className="m-0 flex list-none flex-col gap-3 p-0">
                  {detail.duplicates.map((duplicate) => (
                    <li key={duplicate.case_number} className="flex flex-col gap-1.5">
                      <span className="flex flex-wrap items-center gap-2">
                        <Link href={`${base}${duplicate.case_number}/`} className="font-mono text-[13px] font-medium text-primary hover:underline">
                          {duplicate.case_number}
                        </Link>
                        {duplicate.likely ? (
                          <Chip tone="default" size="xs">
                            {copy.duplicates.likely}
                          </Chip>
                        ) : null}
                        <span className="font-mono text-[11.5px] text-meta">
                          {Math.round(duplicate.score * 100)}% {copy.duplicates.score}
                        </span>
                      </span>
                      <span className="text-[12.5px] leading-[1.45] text-meta">{duplicate.reasons.join(' · ')}</span>
                    </li>
                  ))}
                </ul>
              </Panel>
            ) : null}

            {detail.exports.length || (permissions.export && head.status === 'approved') ? (
              <Panel title={copy.exports.heading}>
                <div className="flex flex-col gap-3">
                  {detail.exports.map((exported) => (
                    <div key={exported.id} className="flex flex-col gap-1.5 rounded-nested border border-green-line bg-green-soft p-3">
                      <span className="flex flex-wrap items-center gap-2 text-[13px] text-secondary">
                        <Chip tone="green" size="xs">
                          v{exported.case_version}
                        </Chip>
                        {shortEmail(exported.created_by_email)} · {formatDateTime(exported.created_at)}
                      </span>
                      <span className="font-mono text-[11px] break-all text-meta">
                        {copy.exports.sha} {exported.content_sha256}
                      </span>
                      {permissions.export ? (
                        <a
                          href={`${here}exports/${exported.id}/`}
                          className="inline-flex min-h-[36px] w-fit items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                        >
                          <DownloadIcon size={16} />
                          {copy.exports.download}
                        </a>
                      ) : null}
                    </div>
                  ))}
                  {permissions.export && head.status === 'approved' ? <ExportE2B caseNumber={caseNumber} revision={revision} /> : null}
                </div>
              </Panel>
            ) : null}
          </aside>
        </div>
      </PageBody>
    </>
  );
}

function SourceView({ detail }: { readonly detail: CaseDetail }) {
  const text = detail.source.text ?? '';
  const highlights: Highlight[] = Object.entries(detail.payload.evidence ?? {})
    .filter(([, evidence]) => evidence.status === 'verified' && text.slice(evidence.start, evidence.end) === evidence.quote)
    .map(([key, evidence]) => ({ start: evidence.start, end: evidence.end, kind: 'evidence', label: key }));
  return (
    <Panel title={copy.source.heading} lead={channelLabel[detail.source.channel] ?? detail.source.channel}>
      <div className="flex flex-col gap-4">
        {detail.source.subject ? (
          <p className="m-0 text-[14px] text-secondary">
            <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.source.subject} </span>
            {detail.source.subject}
          </p>
        ) : null}
        {detail.source.literature?.reference ? (
          <p className="m-0 text-[13.5px] text-secondary">
            <span className="font-mono text-[11px] tracking-[0.08em] text-meta uppercase">{copy.source.literature} </span>
            {detail.source.literature.reference}
          </p>
        ) : null}
        <p className="m-0 rounded-nested border border-hairline bg-panel-header p-4 font-mono text-[13px] leading-[1.75] whitespace-pre-wrap text-secondary">
          <Highlighted text={text} highlights={highlights} tone="verified" />
        </p>
        <p className="m-0 flex items-center gap-2 text-[12.5px] text-meta">
          <span aria-hidden="true" className="inline-block h-3 w-5 rounded-[3px] bg-green-soft shadow-[inset_0_-1.5px_0_var(--color-green-fill)]" />
          {copy.source.legend}
        </p>
      </div>
    </Panel>
  );
}
