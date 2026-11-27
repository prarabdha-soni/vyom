import Link from 'next/link';
import { headerActions, primaryNav } from '@/content/site';
import { ButtonLink, Container } from '@/components/ui';
import { Logo } from './Logo';
import { MegaMenu } from './MegaMenu';
import { MobileNav } from './MobileNav';

export function Header() {
  return (
    <header className="relative z-40 border-b border-hairline bg-surface/85 backdrop-blur-md">
      <Container>
        <nav aria-label="Main" className="relative flex items-center justify-between gap-6 py-3.5">
          <Logo />

          <div className="hidden items-center gap-0.5 lg:flex">
            <MegaMenu />
            {primaryNav.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="flex min-h-[40px] items-center rounded-full px-2.5 text-[14px] font-medium whitespace-nowrap text-secondary transition-colors hover:bg-raised hover:text-primary xl:px-3.5 xl:text-[15px]"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden items-center gap-2 lg:flex">
            <Link
              href={headerActions.secondary.href}
              className="flex min-h-[44px] items-center px-2 text-[14px] font-medium whitespace-nowrap text-secondary transition-colors hover:text-primary xl:px-3.5 xl:text-[15px]"
            >
              {headerActions.secondary.label}
            </Link>
            <ButtonLink href={headerActions.primary.href} className="whitespace-nowrap">{headerActions.primary.label}</ButtonLink>
          </div>

          <MobileNav />
        </nav>
      </Container>
    </header>
  );
}
