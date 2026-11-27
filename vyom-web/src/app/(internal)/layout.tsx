import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { RoleSwitcher, UserMenu } from '@/components/console/ShellClient';
import { loginCopy } from '@/content/console';
import { LogoMark } from '@/components/site';
import { Chip, SampleDataChip } from '@/components/ui';
import { roleLabel } from '@/lib/auth/roles';
import { homePath } from '@/lib/auth/session';
import { getWorkspace } from '@/lib/console/data';

/** Vyom staff only. Never indexed. */
export const metadata: Metadata = {
  title: { default: 'Operations', template: '%s — Vyom' },
  robots: { index: false, follow: false, nocache: true },
};

export default async function InternalLayout({ children }: { readonly children: React.ReactNode }) {
  const workspace = await getWorkspace();
  const { session, me } = workspace;
  if (session.role !== 'ops') redirect(homePath(session.role, session.tenantSlug));

  return (
    <div className="flex min-h-dvh flex-col bg-page">
      <header className="sticky top-0 z-30 flex min-h-[60px] items-center gap-3 border-b border-line bg-surface/90 px-4 backdrop-blur-md sm:px-6 lg:px-8">
        <LogoMark size={26} />
        <span className="text-[15px] font-semibold text-primary">vyom</span>
        <Chip tone="muted" size="xs">
          OPS
        </Chip>
        <div className="ml-auto flex items-center gap-3">
          {workspace.sample ? <SampleDataChip className="hidden sm:inline-block" /> : null}
          {session.mode === 'sample' ? <RoleSwitcher role={session.role} roles={loginCopy.sample.roles} /> : null}
          <UserMenu email={me.user.email} roleName={roleLabel[me.user.role]} initials="OP" />
        </div>
      </header>
      <main id="main" className="flex flex-1 flex-col">
        {children}
      </main>
    </div>
  );
}
