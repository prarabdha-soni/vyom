'use client';

import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { useState } from 'react';
import { headerActions, platformMenu, primaryNav } from '@/content/site';
import { products, statusLabel } from '@/content/products';
import { CloseIcon, MenuIcon, productIcons } from '@/components/icons';
import { ButtonLink, Chip } from '@/components/ui';
import { Logo } from './Logo';

/** The nav for narrow viewports. Radix Dialog gives it a focus trap and Escape. */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          aria-label="Open menu"
          className="flex size-11 cursor-pointer items-center justify-center rounded-button border border-button text-primary lg:hidden"
        >
          <MenuIcon />
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-page/80 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-0 z-50 overflow-y-auto bg-page focus:outline-none">
          <Dialog.Title className="sr-only">Menu</Dialog.Title>
          <Dialog.Description className="sr-only">
            Site navigation and links to every Vyom module.
          </Dialog.Description>

          <div className="flex items-center justify-between border-b border-hairline px-4 py-3.5">
            <Logo />
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close menu"
                className="flex size-11 cursor-pointer items-center justify-center rounded-button border border-button text-primary"
              >
                <CloseIcon />
              </button>
            </Dialog.Close>
          </div>

          <nav aria-label="Main" className="flex flex-col gap-8 px-4 py-8">
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              <li className="pb-2 font-mono text-[11.5px] font-medium tracking-[0.12em] text-meta">
                {platformMenu.heading}
              </li>
              {products.map((product) => {
                const Icon = productIcons[product.slug];
                return (
                  <li key={product.slug}>
                    <Link
                      href={`/products/${product.slug}`}
                      onClick={close}
                      className="flex items-start gap-3 rounded-nested py-2.5"
                    >
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-button border border-strong bg-surface text-primary">
                        <Icon size={18} />
                      </span>
                      <span className="flex min-w-0 flex-col gap-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-[15px] font-semibold text-primary">
                            {product.name}
                          </span>
                          <Chip
                            tone={product.status === 'roadmap' ? 'dashed' : 'default'}
                            size="xs"
                          >
                            {statusLabel[product.status]}
                          </Chip>
                        </span>
                        <span className="text-[13.5px] leading-[1.5] text-muted">
                          {product.summary}
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>

            <ul className="m-0 flex list-none flex-col border-t border-hairline p-0 pt-4">
              {[...platformMenu.footer, ...primaryNav].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    onClick={close}
                    className="flex min-h-[48px] items-center text-[16px] font-medium text-secondary"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-3">
              <ButtonLink href={headerActions.primary.href} size="lg" onClick={close}>
                {headerActions.primary.label}
              </ButtonLink>
              <ButtonLink
                href={headerActions.secondary.href}
                variant="secondary"
                size="lg"
                onClick={close}
              >
                {headerActions.secondary.label}
              </ButtonLink>
            </div>
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
