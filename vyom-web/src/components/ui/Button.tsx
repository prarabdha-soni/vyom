import Link from 'next/link';
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'panel' | 'panelPrimary';
export type ButtonSize = 'md' | 'lg';

/**
 * Padding is keyed by variant *and* size because each pairing uses different
 * horizontal padding. Keeping it in one lookup avoids per-call className
 * overrides, which silently lose to the base classes depending on Tailwind's
 * output order rather than the order you write them.
 *
 * `primary` and `secondary` are the marketing pair (sunlight pill and white
 * pill). `panelPrimary` and `panel` are for actions inside product screens.
 */
const styles: Record<ButtonVariant, { base: string; size: Record<ButtonSize, string> }> = {
  primary: {
    base: 'rounded-full bg-cta font-semibold text-on-cta hover:bg-cta-hover',
    size: {
      md: 'min-h-[44px] px-5 text-[15px]',
      lg: 'min-h-[52px] px-7 text-[16px]',
    },
  },
  secondary: {
    base: 'rounded-full border border-button bg-surface font-medium text-primary hover:border-dash hover:bg-raised',
    size: {
      md: 'min-h-[44px] px-5 text-[15px]',
      lg: 'min-h-[52px] px-6 text-[16px]',
    },
  },
  panelPrimary: {
    base: 'rounded-control bg-ink font-semibold text-on-ink hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-45',
    size: {
      md: 'min-h-[44px] px-[18px] text-[14px]',
      lg: 'min-h-[52px] px-[18px] text-[14px]',
    },
  },
  panel: {
    base: 'rounded-control border border-button bg-surface font-medium text-primary hover:bg-raised disabled:cursor-not-allowed disabled:opacity-45',
    size: {
      md: 'min-h-[44px] px-4 text-[14px]',
      lg: 'min-h-[52px] px-4 text-[14px]',
    },
  },
};

const base =
  'inline-flex items-center justify-center gap-2.5 transition-[background-color,border-color,filter] duration-150';

function classesFor(variant: ButtonVariant, size: ButtonSize, className?: string): string {
  const style = styles[variant];
  return cn(base, style.base, style.size[size], className);
}

type SharedProps = {
  readonly children: ReactNode;
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly className?: string;
};

/** A link styled as a button. */
export function ButtonLink({
  href,
  children,
  variant = 'primary',
  size = 'md',
  className,
  ...rest
}: SharedProps & { readonly href: string } & Omit<
    AnchorHTMLAttributes<HTMLAnchorElement>,
    'href' | 'className' | 'children'
  >) {
  const classes = classesFor(variant, size, className);
  const external = href.startsWith('mailto:') || href.startsWith('http');
  // A download is a file from a route handler, not a page: <Link> would prefetch it on every view.
  const download = rest.download !== undefined && rest.download !== false;

  if (external || download) {
    return (
      <a href={href} className={classes} {...rest}>
        {children}
      </a>
    );
  }

  return (
    <Link href={href} className={classes} {...rest}>
      {children}
    </Link>
  );
}

/** A real <button>, for in-panel controls. */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className,
  type = 'button',
  ...rest
}: SharedProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className' | 'children'>) {
  return (
    <button type={type} className={cn(classesFor(variant, size, className), 'cursor-pointer')} {...rest}>
      {children}
    </button>
  );
}
