import type { Metadata } from 'next';
import { notFound, redirect } from 'next/navigation';
import { ConsoleShell } from '@/components/console/ConsoleShell';
import { getWorkspace } from '@/lib/console/data';

/** The signed-in console is never indexed, whatever site.config says. */
export const metadata: Metadata = {
  title: { default: 'Workspace', template: '%s — Vyom' },
  robots: { index: false, follow: false, nocache: true },
};

export default async function TenantLayout({ children, params }: LayoutProps<'/[tenant_slug]'>) {
  const { tenant_slug: slug } = await params;
  const workspace = await getWorkspace();
  if (workspace.session.role === 'ops') redirect('/ops/');
  if (workspace.me.tenant.slug !== slug) notFound();

  return <ConsoleShell workspace={workspace}>{children}</ConsoleShell>;
}
