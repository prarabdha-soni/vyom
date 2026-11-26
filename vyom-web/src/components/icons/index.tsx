/** Inline SVG icons, traced from the design. No icon package. */

import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement> & { readonly size?: number };

function Icon({ size = 24, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function ArrowRightIcon({ size = 18, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </Icon>
  );
}

export function ChevronDownIcon({ size = 14, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M6 9.5l6 6 6-6" />
    </Icon>
  );
}

export function CheckIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M6 12.5l4 4 8-9" />
    </Icon>
  );
}

/** The tick inside a completed case-run step. Heavier stroke, smaller box. */
export function StepCheckIcon({ size = 12, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={3} {...props}>
      <path d="M6 12.5l4 4 8-9" />
    </Icon>
  );
}

/** Half-filled amber circle: a step waiting on a person. */
export function HalfCircleIcon({ size = 20, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth={2} />
      <path d="M12 5a7 7 0 0 1 0 14z" fill="currentColor" />
    </svg>
  );
}

/** Dashed ring: a step not yet reached. */
export function DashedCircleIcon({ size = 20, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <circle
        cx="12"
        cy="12"
        r="9"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeDasharray="3 3"
      />
    </svg>
  );
}

export function PlusIcon({ size = 16, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M12 5v14M5 12h14" />
    </Icon>
  );
}

export function CloseIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Icon>
  );
}

export function MenuIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} strokeWidth={2} {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Icon>
  );
}

/* --- Product icons ------------------------------------------------------- */

export function CasesIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M4 13.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4.5" />
      <path d="M4 13.5l2.4-7.2A2 2 0 0 1 8.3 5h7.4a2 2 0 0 1 1.9 1.3l2.4 7.2" />
      <path d="M4 13.5h4.2l1.3 2.5h5l1.3-2.5H20" />
    </Icon>
  );
}

export function LiteratureIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M5 4.5h9.5a1.5 1.5 0 0 1 1.5 1.5v4" />
      <path d="M5 4.5v14a1.5 1.5 0 0 0 1.5 1.5H11" />
      <path d="M8 8.5h5M8 11.5h3" />
      <circle cx="16" cy="16" r="3.2" />
      <path d="M18.4 18.4l2.1 2.1" />
    </Icon>
  );
}

export function AuditIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M12 3.5l7 2.8v5.4c0 4.3-2.9 7.6-7 8.8-4.1-1.2-7-4.5-7-8.8V6.3l7-2.8z" />
      <path d="M9 12.2l2.1 2.1 4-4.1" />
    </Icon>
  );
}

export function ReportsIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M14 3.5H7.5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V8z" />
      <path d="M14 3.5V8h4.5" />
      <path d="M8.8 12.5h6.4M8.8 16h4.2" />
    </Icon>
  );
}

export function SignalIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 12l5.2-5.2" />
      <circle cx="15.4" cy="9.6" r="0.9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function OsIcon({ size = 24, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M12 3.5l8.5 4.6L12 12.7 3.5 8.1 12 3.5z" />
      <path d="M3.5 12l8.5 4.6 8.5-4.6" />
      <path d="M3.5 15.9l8.5 4.6 8.5-4.6" />
    </Icon>
  );
}

/* --- Assurance icons ----------------------------------------------------- */

export function ChartIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M4 19.5h16" />
      <path d="M7 16.5v-5M12 16.5V7M17 16.5v-8" />
    </Icon>
  );
}

export function ListIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M9 6.5h11M9 12h11M9 17.5h11" />
      <circle cx="5" cy="6.5" r="1" />
      <circle cx="5" cy="12" r="1" />
      <circle cx="5" cy="17.5" r="1" />
    </Icon>
  );
}

export function LockIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <rect x="5" y="10.5" width="14" height="10" rx="2" />
      <path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3" />
    </Icon>
  );
}

export function PinIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M12 21s-6.5-5.8-6.5-10.8a6.5 6.5 0 0 1 13 0C18.5 15.2 12 21 12 21z" />
      <circle cx="12" cy="10.2" r="2.4" />
    </Icon>
  );
}

/** Vyom Radar: a sweep across concentric range rings. */
export function RadarIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M20.5 12a8.5 8.5 0 1 1-4.2-7.3" />
      <path d="M16.2 12a4.2 4.2 0 1 1-2.1-3.6" />
      <path d="M12 12l6.4-6.4" />
      <circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none" />
    </Icon>
  );
}

/** Vyom Dossier: a bound report with a sealed tab. */
export function DossierIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M8 3.5h7.5l3.5 3.5v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-12.5a2 2 0 0 1 2-2z" />
      <path d="M15.5 3.5V7H19" />
      <path d="M9.2 11h6.6M9.2 14h6.6M9.2 17h3.8" />
      <path d="M4 6.5v12.5a2.5 2.5 0 0 0 2.5 2.5h9" />
    </Icon>
  );
}

export const productIcons = {
  radar: RadarIcon,
  verify: AuditIcon,
  dossier: DossierIcon,
} as const;

export function ShieldIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M12 3.5l7 2.8v5.4c0 4.3-2.9 7.6-7 8.8-4.1-1.2-7-4.5-7-8.8V6.3l7-2.8z" />
    </Icon>
  );
}

export function BanIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M6 18L18 6" />
    </Icon>
  );
}

export function ClockIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.2V12l3 1.8" />
    </Icon>
  );
}

export const securityIcons = {
  pin: PinIcon,
  lock: LockIcon,
  shield: ShieldIcon,
  ban: BanIcon,
  clock: ClockIcon,
  list: ListIcon,
} as const;

export const assuranceIcons = {
  chart: ChartIcon,
  list: ListIcon,
  lock: LockIcon,
  pin: PinIcon,
} as const;

/* --- Home page: problem, module and trust icons --------------------------- */

export function InboxIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M4 13.5l2.4-7.2A1.5 1.5 0 0 1 7.8 5.3h8.4a1.5 1.5 0 0 1 1.4 1l2.4 7.2" />
      <path d="M4 13.5v4.7a1.5 1.5 0 0 0 1.5 1.5h13a1.5 1.5 0 0 0 1.5-1.5v-4.7h-4.6l-1.4 2.4h-4l-1.4-2.4H4z" />
    </Icon>
  );
}

export function PencilIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M15.5 5.5l3 3L9 18l-4 1 1-4 9.5-9.5z" />
      <path d="M13.5 7.5l3 3" />
    </Icon>
  );
}

export function RepeatIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M17 3.5l3 3-3 3" />
      <path d="M4 11.5v-1a4 4 0 0 1 4-4h12" />
      <path d="M7 20.5l-3-3 3-3" />
      <path d="M20 12.5v1a4 4 0 0 1-4 4H4" />
    </Icon>
  );
}

export function UnlinkIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M9.5 14.5l-1.8 1.8a3 3 0 0 1-4.2-4.2l2.8-2.8a3 3 0 0 1 3.6-.5" />
      <path d="M14.5 9.5l1.8-1.8a3 3 0 0 1 4.2 4.2l-2.8 2.8a3 3 0 0 1-3.6.5" />
      <path d="M8 4v2.5M4 8h2.5M16 20v-2.5M20 16h-2.5" />
    </Icon>
  );
}

/** Arrow into a tray: the intake module, distinct from the cases tray. */
export function IntakeIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M12 3.5v10M8 9.5l4 4 4-4" />
      <path d="M4 14.5v3.5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3.5" />
    </Icon>
  );
}

/** Connected nodes: the Live Safety Intelligence module. */
export function NetworkIcon({ size = 22, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <circle cx="6" cy="6.5" r="2.2" />
      <circle cx="18" cy="6.5" r="2.2" />
      <circle cx="12" cy="17.5" r="2.2" />
      <path d="M8.2 6.5h7.6M7.2 8.4l3.7 7.2M16.8 8.4l-3.7 7.2" />
    </Icon>
  );
}

export function LinkIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M10 14a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1 1" />
      <path d="M14 10a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1-1" />
    </Icon>
  );
}

export function UsersIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <circle cx="9" cy="8.5" r="3.2" />
      <path d="M3.5 19.5a5.5 5.5 0 0 1 11 0" />
      <path d="M15.5 5.6a3.2 3.2 0 0 1 0 5.8M17.5 14.6a5.5 5.5 0 0 1 3 4.9" />
    </Icon>
  );
}

export function SlidersIcon({ size = 20, ...props }: IconProps) {
  return (
    <Icon size={size} {...props}>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2" />
      <circle cx="9" cy="17" r="2" />
    </Icon>
  );
}

export const problemIcons = {
  inbox: InboxIcon,
  pencil: PencilIcon,
  repeat: RepeatIcon,
  unlink: UnlinkIcon,
  clock: ClockIcon,
  pin: PinIcon,
} as const;

export const moduleIcons = {
  intake: IntakeIcon,
  cases: CasesIcon,
  reports: ReportsIcon,
  network: NetworkIcon,
  signal: SignalIcon,
  audit: AuditIcon,
} as const;

export const trustIcons = {
  link: LinkIcon,
  users: UsersIcon,
  list: ListIcon,
  sliders: SlidersIcon,
  lock: LockIcon,
  shield: ShieldIcon,
} as const;
