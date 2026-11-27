import type { Metadata } from 'next';
import { aiTaskLabel, humanise, settingsCopy } from '@/content/console';
import { EngineChip, KeyValues, LoadFailed, PageBody, PageHeader, Panel, td, th } from '@/components/console/ui';
import { CheckIcon } from '@/components/icons';
import { Chip, ScrollableTable } from '@/components/ui';
import { ROLES, roleLabel } from '@/lib/auth/roles';
import { getWorkspace, loadProducts, loadSettings } from '@/lib/console/data';
import { formatDate } from '@/lib/console/format';
import { AI_TASKS } from '@/lib/gateway/types';

export const metadata: Metadata = { title: settingsCopy.title };

export default async function SettingsPage() {
  const workspace = await getWorkspace();
  const [settings, products] = await Promise.all([loadSettings(), loadProducts()]);
  const copy = settingsCopy;

  return (
    <>
      <PageHeader
        crumbs={[{ label: workspace.me.tenant.display_name }, { label: copy.title }]}
        title={copy.title}
        lead={copy.lead}
      />
      <PageBody>
        {!settings.ok ? (
          <LoadFailed error={settings.error} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <Panel title={copy.tenant.heading}>
                <KeyValues
                  items={[
                    { label: copy.tenant.name, value: settings.data.tenant.display_name },
                    { label: copy.tenant.slug, value: <span className="font-mono">/{settings.data.tenant.slug}</span> },
                    { label: copy.tenant.kind, value: settings.data.tenant.kind.toUpperCase() },
                    { label: copy.tenant.region, value: settings.data.tenant.residency_region ?? '—' },
                    {
                      label: copy.tenant.hosted,
                      value: settings.data.tenant.hosted_processing_allowed ? copy.tenant.allowed : copy.tenant.notAllowed,
                    },
                    { label: copy.tenant.autoClose, value: settings.data.tenant.auto_close_enabled ? copy.tenant.on : copy.tenant.off },
                  ]}
                />
              </Panel>
              <div className="grid grid-cols-1 gap-5">
                <Panel title={copy.clock.heading}>
                  <KeyValues
                    columns={3}
                    items={[
                      { label: copy.clock.serious, value: `${settings.data.tenant.clock_policy.serious_days} ${copy.clock.days}` },
                      { label: copy.clock.nonSerious, value: `${settings.data.tenant.clock_policy.non_serious_days} ${copy.clock.days}` },
                      { label: copy.clock.policy, value: <span className="font-mono">{settings.data.tenant.clock_policy.version}</span> },
                    ]}
                  />
                </Panel>
                <Panel title={copy.meddra.heading}>
                  <KeyValues
                    items={[
                      {
                        label: copy.meddra.licence,
                        value: settings.data.tenant.meddra.licence_state === 'none' ? copy.meddra.none : humanise(settings.data.tenant.meddra.licence_state),
                      },
                      { label: copy.meddra.dictionary, value: settings.data.tenant.meddra.dictionary ?? '—' },
                    ]}
                  />
                </Panel>
              </div>
            </div>

            <Panel title={copy.ai.heading} bodyClassName="p-0">
              <ScrollableTable label={copy.ai.heading}>
                <table className="w-full min-w-[560px] border-collapse">
                  <thead>
                    <tr>
                      <th scope="col" className={th}>{copy.ai.task}</th>
                      <th scope="col" className={th}>{copy.ai.engine}</th>
                      <th scope="col" className={th}>{copy.ai.region}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {AI_TASKS.map((task) => {
                      const route = settings.data.ai[task];
                      if (!route) return null;
                      return (
                        <tr key={task}>
                          <td className={`${td} text-primary`}>{aiTaskLabel[task]}</td>
                          <td className={td}>
                            <EngineChip isAi={settings.data.ai.is_ai && route.provider !== 'demo'} model={route.model_id} />
                          </td>
                          <td className={`${td} font-mono text-[13px]`}>{route.hosted ? (route.region ?? '—') : copy.ai.local}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </ScrollableTable>
            </Panel>

            {products.ok ? (
              <Panel title={copy.products.heading} bodyClassName="p-0">
                <ScrollableTable label={copy.products.heading}>
                  <table className="w-full min-w-[720px] border-collapse">
                    <thead>
                      <tr>
                        <th scope="col" className={th}>{copy.products.code}</th>
                        <th scope="col" className={th}>{copy.products.form}</th>
                        <th scope="col" className={th}>{copy.products.ibd}</th>
                        <th scope="col" className={th}>{copy.products.rsi}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.data.map((product) => (
                        <tr key={product.code}>
                          <td className={td}>
                            <span className="flex flex-col gap-0.5">
                              <span className="font-mono text-primary">{product.code}</span>
                              <span className="text-[12.5px] text-meta">{product.name}</span>
                            </span>
                          </td>
                          <td className={td}>
                            {humanise(product.dosage_form)} · {product.strength ?? '—'}
                          </td>
                          <td className={td}>{formatDate(product.international_birth_date)}</td>
                          <td className={td}>
                            <span className="flex flex-col gap-0.5">
                              <span>{product.rsi_version ?? '—'}</span>
                              <span className="text-[12.5px] text-meta">
                                {product.reference_safety_terms.length} {copy.products.terms}:{' '}
                                {product.reference_safety_terms.map((term) => term.term).join(', ')}
                              </span>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollableTable>
              </Panel>
            ) : null}

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
              <Panel title={copy.members.heading} bodyClassName="p-0" className="xl:col-span-5">
                <ScrollableTable label={copy.members.heading}>
                  <table className="w-full min-w-[420px] border-collapse">
                    <thead>
                      <tr>
                        <th scope="col" className={th}>{copy.members.email}</th>
                        <th scope="col" className={th}>{copy.members.role}</th>
                        <th scope="col" className={th}>{copy.members.status}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {settings.data.members.map((member) => (
                        <tr key={member.email}>
                          <td className={`${td} text-primary`}>{member.email}</td>
                          <td className={td}>{roleLabel[member.role] ?? member.role}</td>
                          <td className={td}>
                            <Chip tone={member.status === 'active' ? 'green' : 'muted'} size="xs">
                              {member.status.toUpperCase()}
                            </Chip>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollableTable>
              </Panel>

              <Panel title={copy.permissions.heading} lead={copy.permissions.lead} bodyClassName="p-0" className="xl:col-span-7">
                <PermissionMatrix permissions={settings.data.permissions} />
              </Panel>
            </div>
          </>
        )}
      </PageBody>
    </>
  );
}

function PermissionMatrix({ permissions }: { readonly permissions: Partial<Record<string, readonly string[]>> }) {
  const roles = ROLES.filter((role) => role !== 'ops');
  const actions = [...new Set(roles.flatMap((role) => permissions[role] ?? []))].sort();
  return (
    <ScrollableTable label={settingsCopy.permissions.heading}>
      <table className="w-full min-w-[620px] border-collapse">
        <thead>
          <tr>
            <th scope="col" className={th}>
              Action
            </th>
            {roles.map((role) => (
              <th key={role} scope="col" className={`${th} text-center`}>
                {roleLabel[role]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {actions.map((action) => (
            <tr key={action}>
              <th scope="row" className={`${td} text-left font-mono text-[12.5px] font-normal text-primary`}>
                {action}
              </th>
              {roles.map((role) => {
                const allowed = permissions[role]?.includes(action);
                return (
                  <td key={role} className={`${td} text-center`}>
                    {allowed ? (
                      <CheckIcon size={16} className="inline text-green" />
                    ) : (
                      <span aria-hidden="true" className="text-dash">
                        ·
                      </span>
                    )}
                    <span className="sr-only">{allowed ? 'Allowed' : 'Not allowed'}</span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollableTable>
  );
}
