# Vyom

Two applications, docs at the repo root.

```
vyom-web/          Next.js frontend (marketing + auth + tenant app + ops)
vyom-os/           FastAPI (Vyom OS)
BRD-v2             Product brief
system-design.md   Architecture
DESIGN.md          Visual rules — read before changing anything visual
design/            Source-of-truth HTML mock
sample-code.txt
DEPLOY.md          How to ship vyom-web
```

A later backend change for the marketing form should need to touch **only**
`vyom-web/src/lib/api.ts`. Tenant-app calls to FastAPI go through
`vyom-web/src/lib/gateway/api-client.ts`.

The design file `design/Vyom Home Screen.html` is the source of truth for
layout; since 2026-11-27 its colours are superseded by the light palette in
`DESIGN.md`. The build brief is the source of truth for content, structure and
rules. If they conflict, ask.

## Stack — vyom-web

- **Next.js** (App Router). Marketing, login, `/{tenant}` and `/ops` share one
  app. Middleware is the edge gateway (skip marketing; require auth and
  `x-tenant-id` on tenant routes). This is **not** a static export: middleware
  needs a server runtime. Deploy on Vercel with Root Directory `vyom-web`
  (see `DEPLOY.md`). `images.unoptimized: true`.
- **TypeScript**, strict.
- **Tailwind CSS** v4 — tokens defined once in `@theme`, mirrored as CSS variables.
- **Fonts** via `next/font/google`: Instrument Sans (400, 500, 600, 700),
  IBM Plex Mono (400, 500). No other font source.
- **Icons** are inline SVG components in `src/components/icons`. No icon package.
- **Charts** are plain SVG/CSS. No chart library.
- **Radix UI** primitives only where accessibility needs them (navigation menu, dialog).
- **Ask before adding any other dependency.**
- No analytics, cookies, trackers or third-party form services on the **public**
  site. The signed-in stub uses first-party session cookies only.

## Commands

```
cd vyom-web
npm run dev        # local dev server
npm run build      # production build — must pass with zero errors
npm run typecheck  # tsc --noEmit
npm run lint       # eslint
npm run check      # typecheck + lint + build

cd vyom-os
python -m pip install -e '.[test]'
```

## Folder structure — vyom-web

```
src/
  middleware.ts                 EDGE GATEWAY
  app/
    (marketing)/                Public site — Navbar + Footer
      page.tsx                  /
      pricing/                  /pricing
      book-demo/                /book-demo
      products/[slug]/          existing product pages
    (auth)/login/               /login
    (platform)/[tenant_slug]/   Auth + TenantProvider
      dashboard/ console/ settings/
    (internal)/ops/             /ops
  components/
  content/                      All copy lives here
  lib/
    api.ts                      Marketing form boundary
    gateway/api-client.ts       JWT + X-Tenant-ID → vyom-os
    tenant/TenantContext.tsx
site.config.ts
```

## Content rules — non-negotiable

1. **Never invent** customers, logos, testimonials, partnerships, certifications,
   funding or results. If we do not have it, it does not go on the site.
2. **Every number is one of exactly three things:**
   - a **sourced market fact** — the source is shown in small mono text
     (`SOURCE · DELOITTE`);
   - a **target** — labelled as such (`(target)`, `DESIGN TARGETS`);
   - **sample data** — labelled with a `SAMPLE DATA` chip.
   A number that is none of these does not belong on the site.
3. **Sample screens use only fictional identifiers**: drug codes `VY-201`, `VY-305`,
   `VY-412`, case ids `VY-CASE-xxxx`, and `Vendor A`. Vendor A is marked `(FICTIONAL)`.
   The sample tenant is `demo-pharma`, marked `(FICTIONAL)` (agreed 2026-11-27;
   `demo-hospital` and `demo-tpa` are retired), with users at `@demo-pharma.example`.
   **Exception (agreed 2026-10-27):** `/intelligence` shows real public-source
   incidents. Every statement there cites a source that was actually read, the
   content carries a `PUBLIC SOURCE` chip, and a company is named only as the
   cited source names it. Sample screens everywhere else stay fictional.
4. **Never name a competitor.** Compare against "services firms" and
   "software platforms" only.
5. **The Concept preview notice bar** is controlled by one flag in `site.config.ts`
   (`showNotice`).
6. **All copy lives in typed content files** under `src/content/`. Components render
   content; they never hold it. `products.ts` lists the three modules — Vyom Radar,
   Vyom Verify, Vyom Dossier — and has a `flagship` setting, default `"verify"`.
7. **Placeholders stay visibly marked** — `[YOUR EMAIL]` and friends live in
   `site.config.ts` and keep their brackets until the owner replaces them.
8. Blue accent means **AI activity**. Amber means **a human or physician decision**.
   Never mix them. Green means **verified or complete**; rose means **locked or
   overdue**. Output of the rule-based demo engine is not AI and is never blue.
9. **Indian English** spelling, as in the design: "hospitalised", "signal",
   "programme" where it occurs.

## Quality bar

- Matches the design at 1440px; works at 375px and 768px with **no horizontal scroll**.
  Wide tables scroll inside their own box.
- Accessible: semantic landmarks, real buttons and links, visible focus states,
  labelled form fields, 4.5:1 text contrast, `aria-label` on icon-only controls,
  `prefers-reduced-motion` respected.
- Motion: only a subtle fade-and-rise on scroll, and the hero case-run steps appearing
  in sequence once. Nothing loops forever.
- SEO: per-page title and description, Open Graph image, `sitemap.xml`, `robots.txt`.
  **While `site.config.ts` has `indexable: false` (the default), every page emits
  `<meta name="robots" content="noindex">` and `robots.txt` disallows everything.**
  Login, tenant app and `/ops` stay `noindex` even after that flag flips.
- `npm run build`, `npm run typecheck` and `npm run lint` in `vyom-web` pass with
  zero errors.

## Working agreement

After each phase: run the build, take Playwright screenshots at 375, 768 and 1440px,
compare against the design, fix the differences, then commit with a clear message.
