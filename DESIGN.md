# Vyom — Design specification

Extracted from `design/Vyom Home Screen.html` (the approved home page design) on 2026-10-10.
That file is a design-tool export: the real markup lives in its `__bundler/template`
script tag, wrapped in an `<x-dc>` runtime with `{{token}}` placeholders, `sc-raw-*`
table elements and a duplicated static fallback copy. Everything below is the extracted
spec; the runtime itself is discarded.

A token-substituted, browser-renderable copy of the design is kept out of the repo in the
session scratchpad (`design-reference.html`). It renders at 7443px tall at 1440px wide,
matching the design's declared `data-canvas-height="7400"`.

**The design is the source of truth for look. The build prompt is the source of truth for
content, structure and rules.** Where they differ, see "Deviations from the design" at the end.

---

## 1. Tokens

> **Revised 2026-11-27 (owner decision): light theme.** The palette below replaces the
> original dark navy palette across the public site and the signed-in console. Layout,
> type, spacing and the logo are unchanged. The reference for the new look was a set of
> screenshots of a light pharmacovigilance workspace; we match its palette and workspace
> patterns, not its branding, wording or icons.

### Colour

| Token | Hex | Use |
| --- | --- | --- |
| `page` | `#FCFCFD` | Page background |
| `alt` | `#F5F6F9` | Alternating section background, notice bar |
| `surface` | `#FFFFFF` | Cards, header, product frames |
| `raised` | `#F3F4F7` | Hover and selected rows, icon tiles, filled grey chips |
| `panel` / `panel-header` | `#FFFFFF` / `#F8F9FB` | Mock and console panels and their bars |
| `hairline` | `#ECEEF3` | Dividers, table row rules |
| `line` | `#E3E6ED` | Card borders |
| `strong` | `#D6DAE3` | Panel outer border, default chip border |
| `button` | `#D0D5DF` | Secondary button and input borders |
| `dash` | `#AAB1C0` | Dashed chips (`SAMPLE DATA`, `ROADMAP`), not-yet-reached steps |
| `primary` | `#0C0D12` | Headings, strong body |
| `secondary` | `#2A2E38` | Nav links, list items, table body |
| `muted` | `#535968` | Body paragraphs |
| `meta` | `#646A79` | Mono labels, eyebrows, timestamps, sources |
| `accent` | `#2563EB` | **AI activity only.** AI chips, AI steps, AI drafts |
| `amber` | `#B45309` (+ `amber-soft` `#FDF6E8`, `amber-line` `#EFD09A`) | **A human or physician decision** |
| `green` | `#15803D` (+ `green-fill` `#22A559`, `green-soft` `#EDF8F1`) | **Verified, complete, sealed.** Ticks, progress, traceable text |
| `rose` | `#C62D42` (+ `rose-soft` `#FDF0F2`) | **Locked or overdue.** Data lock, overdue clocks |
| `ink` | `#0C0D12` | Primary actions inside product screens, avatars |
| `cta` | `#F7C948` | Marketing call-to-action pill (header, hero, CTA section) |
| `mark` | `#ECEFF5` | Neutral highlight for rule-based (non-AI) text matches |
| `wash-*` | lavender `#E9E6FC`, sky `#E2EDFC`, peach `#FDEADB` | The sky wash only |

**Semantic rule, enforced everywhere:** blue = AI did this; amber = a human decided (or a
decision is waiting on a human); green = verified or complete; rose = locked or overdue.
A step not yet reached is `dash` / `meta`. Output from the rule-based demo engine is
**not** AI and is never blue. Every text colour clears 4.5:1 on `page`, `alt` and `surface`.

### Type

Two families only, both via `next/font/google`:

- **Instrument Sans** — 400, 500, 600, 700. UI and prose.
- **IBM Plex Mono** — 400, 500. All data, chips, labels, eyebrows, timestamps, sources.

| Role | Spec |
| --- | --- |
| H1 | `clamp(44px, 5.4vw, 74px)` / 1.0 / 600 / `-0.035em` |
| H2 | `clamp(32px, 3.3vw, 46px)` / 1.08 / 600 / `-0.025em`, `text-wrap: balance` |
| H2 (CTA section) | `clamp(36px, 4vw, 56px)` / 1.05 / 600 / `-0.03em` |
| H3 flagship | 26px / 1.2 / 600 / `-0.015em` |
| H3 secondary | 22px / 1.22 / 600 / `-0.01em` |
| H3 tertiary | 21px / 1.25 / 600 / `-0.01em` |
| Card title | 17px / 600 |
| Step title | 19px / 600 · Stage title 22px / 600 |
| Lead paragraph | 18px / 1.6 (hero: 19px / 1.6) |
| Body | 16px / 1.5 · card body 15–15.5px / 1.6 |
| Nav / footer link | 15px / 500 |
| Eyebrow | mono 12px / 500 / `0.14em` / uppercase / `accent` |
| Mono label | mono 11px / `0.1em` or 11.5px / `0.08em`–`0.12em`, `text-meta` |
| Chip | mono 11px / 500 / `0.08em` / uppercase |
| Data value | mono 12.5px, `text-primary` |
| Big stat | 48px / 1 / 600 / `-0.03em` (scorecard 28px, targets 30px, stage numeral 44px) |

`text-wrap: balance` on headings, `text-wrap: pretty` on lead paragraphs.

### Shape and spacing

- Container `max-width: 1280px`, `margin: 0 auto`, side padding **32px** (→ **16px** ≤ 640px).
- Section padding **104px** vertical (→ **64px** on phones). Exceptions as designed:
  hero `96px / 104px`, CTA `112px`, standards strip `26px`, footer `64px / 36px`.
- Radii: **16px** cards and panels · **14px** stat/step cards and grid groups ·
  **12px** nested panels and large icon tiles · **10px** buttons and small icon tiles ·
  **8px** in-panel buttons · **6px** chips and marks · **999px** pills · **3–4px** progress bars.
- Borders 1px throughout. **No emoji. No stock illustration.** The only gradients are the
  soft radial glows of the sky wash behind heroes and CTA sections.
- Soft shadows only: `shadow-panel` on product frames and mock panels, `shadow-pop` on
  menus, `shadow-tab` on the active segmented-control tab.
- Interactive targets `min-height: 44px` (hero/CTA buttons 52px).

### Logo

Orbit mark, 30×30, `viewBox="0 0 30 30"`:
- `<ellipse cx=15 cy=15 rx=13 ry=5.2 transform="rotate(-28 15 15)">` stroke `accent`, width 1.6
- `<circle cx=15 cy=15 r=5.4>` fill `text-primary`
- `<circle cx=26.4 cy=8.9 r=2>` fill `accent`

Wordmark "vyom", 24px / 600 / `-0.03em` / `text-primary`, 10px gap from the mark.
Favicon is generated from the mark alone.

---

## 2. Components

### `components/ui`
- **Container** — 1280px, responsive side padding.
- **Section** — `<section>` + vertical rhythm + optional `bg-alt` + bottom hairline.
- **Eyebrow** — mono 12px accent label.
- **Button** — `primary` (sunlight `cta` pill, marketing calls to action), `secondary`
  (white pill, `border-button`), `panelPrimary` (ink, radius 8, actions inside product
  screens), `panel` (white, radius 8).
  Renders `<a>` or `<button>`; sizes `md` (44px) / `lg` (52px).
- **Chip** — mono uppercase, radius 6. Tones: `default`, `accent` (AI), `amber` (human
  decision), `green` (verified/complete), `rose` (locked/overdue), `muted` (filled grey,
  e.g. Draft), `dashed` (`SAMPLE DATA`, `ROADMAP`).
- **Card** — radius 16/14, `bg-card` or `bg-raised`, `border-card` or `accent-line`.
- **StatCard** — big numeral + description + mono source footnote pinned to the bottom.
- **ProgressBar** — track `border-hairline`, fill `accent` / `amber` / `border-dashed`,
  heights 6px and 8px, `min-width: 4px` so tiny values stay visible.

### `components/site`
Header, MegaMenu, Footer, NoticeBar, Logo, SkyWash.

**SkyWash** — absolutely positioned decorative SVG, `aria-hidden`, replacing the dark
starfield. Soft radial glows in `wash-lavender`, `wash-sky` and `wash-peach`, the orbit
ellipses in `strong`, and the accent satellite from the logo. Variants `hero` and `cta`.

**MegaMenu** — the header's **Platform** trigger opens a full-width panel with the three
modules side by side (kicker, name with a sunlight dot, one line on where it takes you)
and links underneath. Radix NavigationMenu with a Viewport anchored to the header.

### `components/mocks`
All carry a `SAMPLE DATA` chip and use only fictional codes (`VY-201`, `VY-305`,
`VY-412`, `VY-CASE-xxxx`) and `Vendor A`.

- **CaseRunPanel** — the hero panel. Header (accent dot with 4px `accent-tint` ring ·
  "Case run" · `VY-CASE-0412` · `SAMPLE DATA`), three context chips, a quoted source
  passage with `<mark>` highlights, a 7-step `<ol>`, and an action bar.
- **CaseQueue** — three rows: id / description / status chip.
- **LiteratureFunnel** — four labelled rows with progress bars (100% / 81% / 4.4% / 0.9%).
- **VendorScorecard** — header, 3-up stat strip, five findings bars, exports footer.
- **ReportOutline**, **SignalBoard** — for the product detail pages.
- **ArchitectureDiagram** — for the platform page.

---

## 3. Home page, section by section

Order is exactly as designed. Nav links point to real routes rather than page anchors.

1. **NoticeBar** (`bg-alt`, bottom border `border-card`, 9px/32px padding, centred mono
   12px). `CONCEPT PREVIEW` in accent 500, then "Product screens show sample data.
   Figures marked as targets are goals we will prove in pilots." Controlled by one flag.

2. **Header** (bottom hairline, 14px/32px). Logo left · nav centre
   (Products ▾, Platform, Vyom Audit, How we start, Company) · "Talk to the founder" +
   accent "Get a free benchmark" right.

3. **Hero** (`#top`, hero starfield, 96px top / 104px bottom, two columns `1 1 480px` and
   `1 1 520px`, 56px gap).
   Pill "AI-NATIVE PHARMACOVIGILANCE · BUILT IN INDIA" with a 6px accent dot.
   H1 three lines, third line accent: *Every case. / Every journal. / Every check.*
   Lead 19px, max 540px. Two buttons (52px). Mono footnote.
   Right: **CaseRunPanel**. Steps: Intake 09:02:11 · Validity 09:02:14 ·
   Coding 09:02:19 · Seriousness 09:02:23 · Narrative 09:02:41 (all blue ticks) ·
   **Physician review — Waiting · evidence attached — `NOW`** (amber half-filled glyph) ·
   E2B(R3) report — Due 24 Oct · 12 days left — `NEXT` (dashed grey ring).
   Footer: Approve / Correct / Escalate + `AI PROPOSES · PHYSICIAN DECIDES`.

4. **Standards strip** (`bg-alt`, 26px padding, `aria-label="Standards Vyom is designed for"`).
   `DESIGNED FOR` then mono 13px: ICH E2B(R3) · MedDRA · WHODrug · EU GVP Module VI ·
   US 21 CFR 314.80 · CDSCO · PvPI · CIOMS AI in PV · India DPDP Act.

5. **The problem** — eyebrow `THE PROBLEM`, H2 "Safety work is growing faster than
   safety teams.", lead, and a rule-topped 19px statement: "The old answer was more
   people. Vyom's answer is AI that does the work, and experts who sign it off."
   Right: 2×2 **StatCard** grid — 40–85% `SOURCE · DELOITTE` · 10–15% `SOURCE · DELOITTE` ·
   1M+ `SOURCE · US FDA` · 47% `SOURCE · GTRI`.

6. **Products** (`#products`, `bg-alt`) — eyebrow `PRODUCTS`, H2 "One safety system.
   Six products.", intro paragraph right-aligned to the heading baseline.
   - Row 1: **Vyom Cases** (flagship, `flex 2`, `bg-raised`, `accent-line` border,
     `FLAGSHIP` chip, H3 26px, **CaseQueue**, chips `PRICED PER CASE` / `DESIGN PARTNERS NOW`)
     and **Vyom Literature** (`flex 1`, H3 22px, **LiteratureFunnel**,
     `PER MOLECULE / MONTH` / `DESIGN PARTNERS NOW`).
   - Row 2, three equal cards: **Vyom Audit** (`PER CASE CHECKED` / `DESIGN PARTNERS NOW`),
     **Vyom Reports** (`PER REPORT` / `ROADMAP`), **Vyom Signal** (`SUBSCRIPTION` / `ROADMAP`).
   - Row 3: **Vyom OS**, a wide horizontal card — 48px icon tile, `ROADMAP` chip,
     `ANNUAL LICENCE`, and an accent link "Talk to us about licensing →".

7. **Platform** (`#platform`) — eyebrow `PLATFORM`, H2 "AI proposes. Rules check.
   Experts decide.", lead. Five step cards:
   `01 · SYSTEM` Ingest → `02 · AI AGENTS` Understand (accent border + accent label) →
   `03 · RULES` Check → `04 · EXPERTS` Decide (amber border + amber label) →
   `05 · SYSTEM` Deliver (no trailing arrow).
   Below, a 1px-gap grid of four assurance rows: evaluation gate · audit trail ·
   isolated encrypted data · hosted in India with zero-retention model providers.

8. **Vyom Audit** (`#audit`, `bg-alt`) — eyebrow `VYOM AUDIT`, H2 "Check every case.
   Whoever processed it.", lead, three accent-ticked bullets (the third ends "(target)"),
   CTA button. Right: **VendorScorecard** — `VENDOR A (FICTIONAL) · Q3 2026`,
   CASES CHECKED 2,400 · COVERAGE 100% (accent) · FINDINGS 194 (amber);
   five findings bars (3.1% / 2.4% / 1.2% / 0.8% / 0.6%, drawn at 100/78/39/26/19% width);
   exports footer.

9. **How we start** (`#proof`) — eyebrow `HOW WE START`, H2 "Proof before price.", lead.
   Three stage cards: **01** Retrospective benchmark `WEEKS 1–2 · FREE` (accent numeral
   and border) · **02** Parallel run `WEEKS 3–10` · **03** Production `WEEK 11 ONWARD`.
   Then `WHAT EVERY PILOT MUST PROVE · DESIGN TARGETS` over a four-cell target grid:
   ≥ 50% · ≥ baseline · 100% · < 48 h.

10. **Why Vyom** (`#why`, `bg-alt`) — eyebrow `WHY VYOM`, H2 "Built to replace the
    people-heavy model.", lead. A comparison table, `min-width: 760px` inside an
    `overflow-x: auto` rounded box, columns COMPARE / SERVICES FIRMS / SOFTWARE PLATFORMS /
    **VYOM** (accent header, `accent-tint` column). Five rows: What you pay for · Who does
    the work · Quality evidence · Independent audit of any vendor · Time to go live.
    Row labels are `<th scope="row">`.

11. **CTA** (`#benchmark`, cta starfield, 112px padding, centred, max 760px) —
    eyebrow `DESIGN PARTNERS`, H2 "Become a Vyom design partner.", lead, two buttons,
    and `[YOUR EMAIL] · GURUGRAM, INDIA` in mono.

12. **Footer** (`#company`, `bg-page`, 64px top / 36px bottom) — logo, tagline
    "AI-native drug safety, built in India for the world.", `GURUGRAM, INDIA`, and three
    link columns (PRODUCTS ×6, PLATFORM ×4, COMPANY ×3). Bottom bar above a hairline:
    "© 2026 Vyom. Concept preview: product screens show sample data." and
    "Vyom (व्योम) is Sanskrit for sky."

---

## 4. Responsive behaviour

The design is built on `flex-wrap` with `flex-basis` hints and
`grid-template-columns: repeat(auto-fit, minmax(min(Npx, 100%), 1fr))`, so it reflows
without media queries. Verified: no horizontal scroll at 1440 / 768 / 375px
(heights 7443 / 10410 / 15948px). We keep that approach and add only:

- Container side padding 32px → 16px at ≤ 640px.
- Section padding 104px → 64px at ≤ 640px.
- Header nav collapses into a dialog-based menu below the `lg` breakpoint.
- The comparison table keeps `min-width: 760px` and scrolls inside its own box.

## 5. Motion

Only two, both one-shot, both disabled under `prefers-reduced-motion: reduce`:

1. A subtle fade-and-rise as sections enter the viewport (IntersectionObserver, once).
2. The hero case-run steps appearing in sequence, once, on load.

Nothing loops. Nothing animates indefinitely.

## 6. Accessibility

Semantic `header` / `nav` / `main` / `section` / `footer`; one `h1`; headings in order.
Real `<button>` and `<a>`. Visible focus rings in accent on every interactive element.
`aria-hidden` on all decorative SVG. `aria-label` on icon-only controls and on each
footer `<nav>`. Table uses `<th scope>`. Body text meets 4.5:1 on its background
(`text-muted #A7B2C6` on `#070B14` ≈ 9.2:1; `text-meta #8290A8` on `#070B14` ≈ 6.3:1;
`on-accent #06101F` on `accent #62AEF2` ≈ 10.4:1).

---

## 7. Deviations from the design

Recorded so they are deliberate, not drift:

1. **Nav and footer links go to real routes**, not `#anchors` (required by the prompt).
   `Vyom Audit` → `/products/audit`; `How we start` → `/how-we-start`;
   `Company` → `/company`; `Contact` → `/contact`; the two CTA buttons → `/contact`.
2. **Products opens an accessible mega-menu** listing all six products with one-line
   descriptions and status chips. The design shows only a chevron.
3. **Privacy and Terms links** are added to the footer bottom bar; the design has none,
   but the prompt requires both routes.
4. **`[YOUR EMAIL]`** stays visibly marked until replaced; it lives in `site.config.ts`.
5. **Phone padding** (16px side, 64px section) is added; the design is a fixed 1440px canvas.
6. **Light theme (2026-11-27).** The original dark navy palette is replaced by the light
   palette in section 1, on the owner's instruction. The design mock still governs layout.
7. **Three modules (2026-11-27).** The six products became Vyom Radar (intake and
   literature), Vyom Verify (cases, medical review and quality checks) and Vyom Dossier
   (periodic reports). Old product URLs redirect to the matching module.
