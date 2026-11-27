/**
 * Decorative sky wash: soft lavender, sky and peach light with faint orbit
 * lines and one accent satellite. Purely visual, never announced. The only
 * gradients on the site live here.
 */

type SkyWashProps = {
  readonly variant?: 'hero' | 'cta';
};

export function SkyWash({ variant = 'hero' }: SkyWashProps) {
  const isHero = variant === 'hero';
  const id = isHero ? 'sky-hero' : 'sky-cta';

  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox={isHero ? '0 0 1440 800' : '0 0 1440 600'}
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <defs>
        <Glow id={`${id}-lavender`} color="var(--color-wash-lavender)" />
        <Glow id={`${id}-sky`} color="var(--color-wash-sky)" />
        <Glow id={`${id}-peach`} color="var(--color-wash-peach)" />
      </defs>

      {isHero ? (
        <>
          <circle cx="1120" cy="90" r="680" fill={`url(#${id}-lavender)`} />
          <circle cx="1380" cy="560" r="520" fill={`url(#${id}-sky)`} />
          <circle cx="60" cy="820" r="620" fill={`url(#${id}-peach)`} />
          <Orbits cx={1010} cy={420} rx={[720, 560, 400]} ry={[300, 230, 160]} rotate={-14} />
          <Satellite cx={1233.5} cy={159} />
        </>
      ) : (
        <>
          <circle cx="1240" cy="40" r="560" fill={`url(#${id}-lavender)`} />
          <circle cx="160" cy="600" r="540" fill={`url(#${id}-peach)`} />
          <circle cx="760" cy="640" r="420" fill={`url(#${id}-sky)`} />
          <Orbits cx={720} cy={300} rx={[740, 560]} ry={[260, 190]} rotate={0} />
          <Satellite cx={1178.7} cy={191} />
        </>
      )}
    </svg>
  );
}

function Glow({ id, color }: { readonly id: string; readonly color: string }) {
  return (
    <radialGradient id={id}>
      <stop offset="0%" stopColor={color} stopOpacity="1" />
      <stop offset="55%" stopColor={color} stopOpacity="0.55" />
      <stop offset="100%" stopColor={color} stopOpacity="0" />
    </radialGradient>
  );
}

function Orbits({
  cx,
  cy,
  rx,
  ry,
  rotate,
}: {
  readonly cx: number;
  readonly cy: number;
  readonly rx: readonly number[];
  readonly ry: readonly number[];
  readonly rotate: number;
}) {
  return (
    <g fill="none" stroke="var(--color-strong)" strokeWidth="1">
      {rx.map((radius, index) => (
        <ellipse
          key={radius}
          cx={cx}
          cy={cy}
          rx={radius}
          ry={ry[index]}
          transform={`rotate(${rotate} ${cx} ${cy})`}
          strokeDasharray={index === 0 ? '2 7' : undefined}
          strokeOpacity={index === 0 ? 0.9 : 0.6}
        />
      ))}
    </g>
  );
}

/** The accent satellite from the logo: a filled dot inside a faint ring. */
function Satellite({ cx, cy }: { readonly cx: number; readonly cy: number }) {
  return (
    <>
      <circle cx={cx} cy={cy} r="7" fill="none" stroke="var(--color-accent)" strokeOpacity="0.35" strokeWidth="1" />
      <circle cx={cx} cy={cy} r="3" fill="var(--color-accent)" />
    </>
  );
}
