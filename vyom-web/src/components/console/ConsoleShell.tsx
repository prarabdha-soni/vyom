import type { ReactNode } from 'react';
import { consoleShell, loginCopy } from '@/content/console';
import { cn } from '@/lib/cn';
import { Chip, SampleDataChip } from '@/components/ui';
import { roleLabel } from '@/lib/auth/roles';
import { initials } from '@/lib/console/format';
import type { Workspace } from '@/lib/console/data';
import { MobileConsoleNav, Rail, RoleSwitcher, UserMenu } from './ShellClient';
import { EngineChip } from './ui';

/** Rail on the left, top bar with tenant, mode and account, then the page. */
export function ConsoleShell({ workspace, children }: { readonly workspace: Workspace; readonly children: ReactNode }) {
  const { me, session } = workspace;
  const tenant = me.tenant;
  const base = `/${tenant.slug}`;
  const name = tenant.display_name.replace(/\s*\(FICTIONAL\)\s*/i, '');
  const sampleRoles = loginCopy.sample.roles;

  return (
    <div className="flex min-h-dvh bg-page">
      <Rail base={base} tenantName={tenant.display_name} tenantInitials={initials(name)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex min-h-[60px] items-center gap-3 border-b border-line bg-surface/90 px-4 backdrop-blur-md sm:px-6 lg:px-8">
          <MobileConsoleNav base={base} />
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            {/* On a phone the role menu needs the room; the breadcrumb below names the tenant. */}
            <span
              className={cn(
                'truncate text-[15px] font-semibold tracking-[-0.01em] text-primary',
                session.mode === 'sample' && 'hidden sm:block',
              )}
            >
              {name}
            </span>
            {tenant.is_fictional ? (
              <Chip tone="dashed" size="xs">
                FICTIONAL
              </Chip>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            {tenant.is_fictional ? <SampleDataChip className="hidden md:inline-block" /> : null}
            <span className="hidden xl:inline-flex">
              <EngineChip isAi={me.ai.is_ai} />
            </span>
            {session.mode === 'sample' ? <RoleSwitcher role={session.role} roles={sampleRoles} /> : null}
            <UserMenu email={me.user.email} roleName={roleLabel[me.user.role]} initials={me.user.email.slice(0, 2).toUpperCase()} />
          </div>
        </header>
        {session.mode === 'sample' ? (
          <p className="m-0 border-b border-dashed border-dash bg-raised px-4 py-2 text-[12.5px] leading-[1.45] text-secondary sm:px-6 lg:px-8">
            {consoleShell.sampleBanner}
          </p>
        ) : null}
        <main id="main" className="flex min-w-0 flex-1 flex-col">
          {children}
        </main>
      </div>
    </div>
  );
}
