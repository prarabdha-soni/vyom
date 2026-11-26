'use client';

import * as NavigationMenu from '@radix-ui/react-navigation-menu';
import Link from 'next/link';
import { products } from '@/content/products';
import { platformMenu } from '@/content/site';
import { ArrowRightIcon, ChevronDownIcon } from '@/components/icons';

/**
 * The Platform mega-menu: the three modules side by side, each a large card
 * with its kicker, name and one line on where it takes you. Radix handles the
 * roving focus, Escape and aria-expanded wiring.
 *
 * Radix wraps the List in its own positioned element, so content placed
 * inside the Item would anchor to the trigger. The panel renders into a
 * Viewport instead, whose wrapper anchors to the header's <nav> (the nearest
 * positioned ancestor) and spans the full container width.
 */
export function MegaMenu() {
  return (
    // Radix labels its <nav> "Main" by default, which would duplicate the
    // header landmark it sits inside.
    <NavigationMenu.Root aria-label={platformMenu.label} delayDuration={0}>
      <NavigationMenu.List className="m-0 flex list-none p-0">
        <NavigationMenu.Item>
          <NavigationMenu.Trigger className="group flex min-h-[40px] cursor-pointer items-center gap-1.5 rounded-full px-3.5 text-[14px] font-medium whitespace-nowrap text-secondary transition-colors hover:bg-raised hover:text-primary data-[state=open]:bg-raised data-[state=open]:text-primary xl:px-4 xl:text-[15px]">
            {platformMenu.label}
            <ChevronDownIcon className="transition-transform duration-200 group-data-[state=open]:rotate-180" />
          </NavigationMenu.Trigger>

          <NavigationMenu.Content className="w-full">
            <div className="rounded-panel border border-line bg-surface p-3 shadow-pop">
              <ul className="m-0 grid list-none grid-cols-3 gap-2 p-0">
                {products.map((product) => (
                  <li key={product.slug} className="flex">
                    <NavigationMenu.Link asChild>
                      <Link
                        href={`/products/${product.slug}`}
                        className="group/card flex w-full flex-col gap-3 rounded-card border border-transparent p-6 transition-colors hover:border-line hover:bg-page focus-visible:border-line"
                      >
                        <span className="font-mono text-[11px] tracking-[0.12em] text-meta">
                          {product.kicker}
                        </span>
                        <span className="flex items-baseline gap-2 text-[26px] leading-none font-normal tracking-[-0.02em] text-primary">
                          <span aria-hidden="true" className="size-2 shrink-0 -translate-y-1 rounded-full bg-cta" />
                          {product.shortName}
                        </span>
                        <span className="text-[14.5px] leading-[1.5] text-muted">{product.summary}</span>
                        <span className="mt-auto inline-flex items-center gap-1.5 pt-2 text-[13.5px] font-medium text-secondary group-hover/card:text-primary">
                          {product.name}
                          <ArrowRightIcon size={14} className="transition-transform group-hover/card:translate-x-0.5" />
                        </span>
                      </Link>
                    </NavigationMenu.Link>
                  </li>
                ))}
              </ul>

              <ul className="m-0 mt-2 flex list-none flex-wrap gap-x-2 border-t border-hairline p-0 pt-2">
                {platformMenu.footer.map((link) => (
                  <li key={link.href}>
                    <NavigationMenu.Link asChild>
                      <Link
                        href={link.href}
                        className="flex min-h-[44px] items-center gap-2 rounded-control px-3 text-[14px] font-medium text-secondary transition-colors hover:bg-raised hover:text-primary"
                      >
                        {link.label}
                        <ArrowRightIcon size={14} />
                      </Link>
                    </NavigationMenu.Link>
                  </li>
                ))}
              </ul>
            </div>
          </NavigationMenu.Content>
        </NavigationMenu.Item>
      </NavigationMenu.List>

      <div className="pointer-events-none absolute inset-x-0 top-full z-50 pt-2">
        <NavigationMenu.Viewport className="pointer-events-auto h-[var(--radix-navigation-menu-viewport-height)] w-full" />
      </div>
    </NavigationMenu.Root>
  );
}
