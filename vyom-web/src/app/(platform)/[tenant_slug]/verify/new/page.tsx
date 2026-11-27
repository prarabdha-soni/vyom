import type { Metadata } from 'next';
import { verifyCopy } from '@/content/console';
import { IntakeForm } from '@/components/console/verify/IntakeForm';
import { PageBody, PageHeader, Panel } from '@/components/console/ui';
import { can, getWorkspace } from '@/lib/console/data';

export const metadata: Metadata = { title: verifyCopy.intake.title };

export default async function NewCasePage({ params }: PageProps<'/[tenant_slug]/verify/new'>) {
  const { tenant_slug: slug } = await params;
  const workspace = await getWorkspace();
  const base = `/${slug}/verify/`;
  return (
    <>
      <PageHeader
        crumbs={[
          { label: workspace.me.tenant.display_name, href: `/${slug}/dashboard/` },
          { label: verifyCopy.title, href: base },
          { label: verifyCopy.intake.title },
        ]}
        title={verifyCopy.intake.title}
        lead={verifyCopy.intake.lead}
      />
      <PageBody>
        <Panel className="max-w-[920px]">
          {can(workspace, 'case.create') ? (
            <IntakeForm today={workspace.today} cancelHref={base} />
          ) : (
            <p className="m-0 text-[14px] text-muted">{verifyCopy.intake.cannot}</p>
          )}
        </Panel>
      </PageBody>
    </>
  );
}
