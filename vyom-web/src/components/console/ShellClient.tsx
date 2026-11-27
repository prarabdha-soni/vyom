'use client';

import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { consoleShell } from '@/content/console';
import {
  AuditIcon,
  CheckIcon,
  ChevronDownIcon,
  CloseIcon,
  DossierIcon,
  GridIcon,
  HistoryIcon,
  MenuIcon,
  RadarIcon,
  SignOutIcon,
  SlidersIcon,
} from '@/components/icons';
import { LogoMark } from '@/components/site';
import { signOut, switchSampleRole } from '@/lib/auth/actions';
import { cn } from '@/lib/cn';

const icons = {
  dashboard: GridIcon,
  radar: RadarIcon,
  verify: AuditIcon,
  dossier: DossierIcon,
  audit: HistoryIcon,
  settings: SlidersIcon,
} as const;

function useActive(base: string) {
  const pathname = usePathname() ?? '';
  return (segment: string) => pathname.startsWith(`${base}/${segment}`);
}

/** The desktop icon rail. */
export function Rail({ base, tenantName, tenantInitials }: { readonly base: string; readonly tenantName: string; readonly tenantInitials: string }) {
  const active = useActive(base);
  return (
    <aside className="sticky top-0 hidden h-dvh w-[84px] shrink-0 flex-col items-center border-r border-line bg-surface py-4 lg:flex">
      <Link href={`${base}/dashboard/`} aria-label="Vyom dashboard" className="flex size-11 items-center justify-center rounded-button">
        <LogoMark size={28} />
      </Link>
      <nav aria-label={consoleShell.navLabel} className="mt-6 flex-1">
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
          {consoleShell.nav.map((item) => {
            const Icon = icons[item.key];
            const current = active(item.segment);
            return (
              <li key={item.key}>
                <Link
                  href={`${base}/${item.segment}/`}
                  aria-current={current ? 'page' : undefined}
                  className={cn(
                    'group flex w-[68px] flex-col items-center gap-1 rounded-button py-1.5 text-[11px] font-medium transition-colors',
                    current ? 'text-primary' : 'text-meta hover:text-primary',
                  )}
                >
                  <span
                    className={cn(
                      'flex size-9 items-center justify-center rounded-control transition-colors',
                      current ? 'bg-ink text-on-ink' : 'group-hover:bg-raised',
                    )}
                  >
                    <Icon size={19} />
                  </span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <span
        title={tenantName}
        className="flex size-10 items-center justify-center rounded-button border border-line bg-raised font-mono text-[12px] font-medium text-primary"
      >
        <span aria-hidden="true">{tenantInitials}</span>
        <span className="sr-only">{tenantName}</span>
      </span>
    </aside>
  );
}

/** The navigation drawer below the lg breakpoint. */
export function MobileConsoleNav({ base }: { readonly base: string }) {
  const [open, setOpen] = useState(false);
  const active = useActive(base);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        aria-label={consoleShell.menuOpen}
        className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-control border border-line text-primary lg:hidden"
      >
        <MenuIcon size={20} />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-primary/25" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 flex w-[min(300px,85vw)] flex-col gap-6 border-r border-line bg-surface p-4 shadow-pop focus:outline-none">
          <div className="flex items-center justify-between">
            <Dialog.Title className="m-0 flex items-center gap-2 text-[17px] font-semibold text-primary">
              <LogoMark size={24} /> vyom
            </Dialog.Title>
            <Dialog.Close
              aria-label={consoleShell.menuClose}
              className="flex size-10 cursor-pointer items-center justify-center rounded-control text-primary hover:bg-raised"
            >
              <CloseIcon size={20} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">{consoleShell.navLabel}</Dialog.Description>
          <nav aria-label={consoleShell.navLabel}>
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {consoleShell.nav.map((item) => {
                const Icon = icons[item.key];
                const current = active(item.segment);
                return (
                  <li key={item.key}>
                    <Link
                      href={`${base}/${item.segment}/`}
                      onClick={() => setOpen(false)}
                      aria-current={current ? 'page' : undefined}
                      className={cn(
                        'flex min-h-[44px] items-center gap-3 rounded-control px-3 text-[15px] font-medium',
                        current ? 'bg-ink text-on-ink' : 'text-secondary hover:bg-raised',
                      )}
                    >
                      <Icon size={19} />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Sample workspace only: change role without signing out. */
/** A menu that closes on Escape (returning focus to its trigger) or a click outside. */
function usePopover() {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      trigger.current?.focus();
    };
    const onClick = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  return { open, toggle: () => setOpen((value) => !value), root, trigger };
}

/**
 * Sample workspace only: view the console as another role. Each role is its
 * own submit button, so nothing changes until one is chosen.
 */
export function RoleSwitcher({
  role,
  roles,
}: {
  readonly role: string;
  readonly roles: readonly { readonly value: string; readonly label: string }[];
}) {
  const pathname = usePathname() ?? '';
  const { open, toggle, root, trigger } = usePopover();
  const current = roles.find((option) => option.value === role)?.label ?? role;
  const label = consoleShell.roleSwitch.label;
  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={toggle}
        className="flex min-h-[36px] cursor-pointer items-center gap-2 rounded-control border border-button bg-surface px-2.5 text-[13.5px] font-medium text-primary hover:bg-raised"
      >
        <span className="hidden font-mono text-[11px] tracking-[0.08em] whitespace-nowrap text-meta uppercase xl:inline">{label}</span>
        <span className="sr-only xl:hidden">{label}: </span>
        <span className="max-w-[140px] truncate">{current}</span>
        <ChevronDownIcon size={14} aria-hidden="true" />
      </button>
      {open ? (
        <form
          action={switchSampleRole}
          aria-label={label}
          className="absolute top-full right-0 z-40 mt-2 flex w-[220px] flex-col gap-0.5 rounded-card border border-line bg-surface p-1.5 shadow-pop"
        >
          <input type="hidden" name="path" value={pathname} />
          {roles.map((option) => (
            <button
              key={option.value}
              type="submit"
              name="role"
              value={option.value}
              aria-current={option.value === role ? 'true' : undefined}
              className="flex min-h-[40px] w-full cursor-pointer items-center justify-between gap-2 rounded-control px-2.5 text-left text-[14px] text-secondary hover:bg-raised aria-[current=true]:font-medium aria-[current=true]:text-primary"
            >
              {option.label}
              {option.value === role ? <CheckIcon size={16} aria-hidden="true" /> : null}
            </button>
          ))}
        </form>
      ) : null}
    </div>
  );
}

/** Avatar button with the signed-in identity and sign-out. */
export function UserMenu({ email, roleName, initials }: { readonly email: string; readonly roleName: string; readonly initials: string }) {
  const { open, toggle, root, trigger } = usePopover();

  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-label={consoleShell.userMenu}
        aria-expanded={open}
        aria-haspopup="true"
        onClick={toggle}
        className="flex size-9 cursor-pointer items-center justify-center rounded-full bg-ink font-mono text-[12px] font-medium text-on-ink"
      >
        {initials}
      </button>
      {open ? (
        <div className="absolute top-full right-0 z-40 mt-2 flex w-[260px] flex-col gap-3 rounded-card border border-line bg-surface p-3 shadow-pop">
          <div className="flex flex-col gap-0.5 px-1">
            <span className="truncate text-[14px] font-medium text-primary">{email}</span>
            <span className="text-[13px] text-meta">{roleName}</span>
          </div>
          <div className="flex flex-col gap-1 border-t border-hairline pt-2">
            <Link href="/" className="flex min-h-[40px] items-center rounded-control px-2 text-[14px] text-secondary hover:bg-raised">
              {consoleShell.publicSite}
            </Link>
            <form action={signOut}>
              <button
                type="submit"
                className="flex min-h-[40px] w-full cursor-pointer items-center gap-2 rounded-control px-2 text-left text-[14px] text-secondary hover:bg-raised"
              >
                <SignOutIcon />
                {consoleShell.signOut}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
