---
name: StatementX
description: Warm paper-ledger design system for the StatementX bookkeeping admin panel
colors:
  paper-ground: "#f3ede3"
  ledger-white: "#fffdf8"
  parchment-muted: "#f4ede2"
  cream-raised: "#fffaf2"
  rule-line: "#d9cfbe"
  rule-strong: "#c5b79e"
  ledger-ink: "#1f2937"
  pencil-gray: "#667085"
  ledger-teal: "#0f766e"
  ledger-teal-deep: "#115e59"
  annotation-amber: "#b45309"
  clerk-green: "#166534"
  red-ink: "#b91c1c"
  night-desk: "#0f151c"
  dark-ledger: "#16202a"
  dark-surface-muted: "#101821"
  dark-raised: "#1b2632"
  dark-rule: "#293847"
  dark-rule-strong: "#3a4f61"
  moon-ink: "#edf2f7"
  cloud-gray: "#9aa8ba"
  signal-teal: "#2db6a3"
  signal-teal-bright: "#63d3c3"
  lantern-amber: "#f59e0b"
  meadow-green: "#4ade80"
  alarm-coral: "#f87171"
typography:
  headline:
    fontFamily: "Manrope, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Manrope, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.35
  body:
    fontFamily: "Manrope, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Manrope, Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "10.5px"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0.08em"
  mono:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  control: "10px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
components:
  button-primary:
    backgroundColor: "{colors.ledger-teal}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "{colors.cream-raised}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  button-danger:
    backgroundColor: "{colors.red-ink}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  surface-card:
    backgroundColor: "{colors.ledger-white}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.md}"
  input-field:
    backgroundColor: "{colors.cream-raised}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.sm}"
    height: "34px"
  chip-account-mapped:
    backgroundColor: "rgba(15, 118, 110, 0.10)"
    textColor: "{colors.ledger-teal}"
    rounded: "{rounded.pill}"
    padding: "4px 8px"
  chip-account-flagged:
    backgroundColor: "rgba(180, 83, 9, 0.10)"
    textColor: "{colors.annotation-amber}"
    rounded: "{rounded.pill}"
    padding: "4px 8px"
  chip-group:
    backgroundColor: "{colors.parchment-muted}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
---

# Design System: StatementX

## Overview

**Creative North Star: "The Warm Paper Ledger"**

StatementX looks like a well-kept accounting ledger lying on a warm wooden desk. The ground is warm parchment (`--color-bg #f3ede3` light, `#0f151c` dark) washed with faint amber and teal radial glows; every working surface is a paper card (`#fffdf8` light, `#16202a` dark) ruled with one-pixel hairlines, the way a ledger page is ruled. Color behaves like a clerk's pens: teal ink does the confirming and the acting, amber ink flags anything that needs a human decision, red ink is reserved for destruction. Nothing shouts; density is comfortable, not cramped, because the users are mixed-skill bookkeeping staff, some not accountants by training.

The system is token-first: every color, radius, shadow, and font stack lives as a CSS custom property in `admin_frontend/src/style.css` with a parallel `html.dark` variant block, and Tailwind is configured to read those variables. Components never hardcode hex values; they compose tokens. UI copy mixes English and Indonesian naturally — numbers and dates always set in the mono voice so they read as ledger figures regardless of language.

**Key Characteristics:**
- Warm paper ground with radial amber/teal washes; cream card surfaces with hairline borders
- Dual-theme by CSS variables (`:root` light, `html.dark` dark) — no component knows which theme is active
- Teal = action/confirm/mapped; amber = needs attention; red = destructive only
- Manrope for the UI voice, IBM Plex Mono for every numeral a clerk scans
- One-pixel hairline ruling between table cells and card sections
- Soft ambient card shadows, always on; hover responses tint rows and lift buttons, never shadow-pop tables
- Pill-shaped status chips built from ~10% alpha tints, not solid fills
- Bootstrap Icons throughout, 10–14px, always token-colored

## Colors

The palette reads as stationery, not software: parchment and cream neutrals carrying a deep ledger teal and a single annotation amber. All values below are CSS variables defined in `admin_frontend/src/style.css`; the frontmatter records the light-theme canonical values, and each entry names its dark equivalent. Components reference the variables (`var(--color-primary)`), so dark mode is a token swap, not a restyle.

### Primary
- **Ledger Teal** (`--color-primary`, light `#0f766e` / dark "Signal Teal" `#2db6a3`): the working ink. Primary buttons (Assign, save actions), mapped-account chips, focus rings, links of intent, active sidebar items, selection tints at 4–10% alpha. Its deeper step **Ledger Teal Deep** (`--color-primary-strong #115e59` / `#63d3c3`) darkens button hovers.

### Secondary
- **Annotation Amber** (`--color-accent` == `--color-warning`, light `#b45309` / dark "Lantern Amber" `#f59e0b`): the flag pen. Unmapped and mixed account chips, the dots on attention-queue group chips, eyebrow labels, any state meaning "a human decision is pending here."

### Tertiary
- **Clerk Green** (`--color-success`, light `#166534` / dark `#4ade80`): quiet confirmation only — the all-clear icon, success status pills. Never a button.
- **Red Ink** (`--color-danger`, light `#b91c1c` / dark `#f87171`): destruction and error — delete buttons and delete-hover states. Reserved; see the Amber-Flags-Work Rule below.

### Neutral
- **Paper Ground** (`--color-bg`, light `#f3ede3` / dark "Night Desk" `#0f151c`): app backdrop, always under the amber/teal radial washes.
- **Ledger White** (`--color-surface`, light `#fffdf8` / dark "Dark Ledger" `#16202a`): card and panel surfaces.
- **Parchment Muted** (`--color-surface-muted`, light `#f4ede2` / dark `#101821`): table headers, chip and issue-row fills, ghost-button hover ground.
- **Cream Raised** (`--color-surface-raised`, light `#fffaf2` / dark `#1b2632`): inputs, secondary buttons, open editor pods — the layer that sits *on* a card.
- **Rule Line** (`--color-border`, light `#d9cfbe` / dark `#293847`): the hairline ruling — cell borders, card borders, dividers.
- **Rule Strong** (`--color-border-strong`, light `#c5b79e` / dark `#3a4f61`): emphasized rules — header underlines, hover borders, pressed chips.
- **Ledger Ink** (`--color-text`, light `#1f2937` / dark "Moon Ink" `#edf2f7`): primary text.
- **Pencil Gray** (`--color-text-muted`, light `#667085` / dark "Cloud Gray" `#9aa8ba`): labels, captions, secondary values, icons at rest.

### Named Rules
**The Amber-Flags-Work Rule.** Teal means the system is acting or confirming; amber means a human must decide; red means something will be destroyed. A surface never borrows red for decoration or amber for success.

**The Tint-Not-Fill Rule.** Status chips and selection states are ~10% alpha tints with a ~22–24% alpha border and the solid token as text color — never solid color fills. (Known quirk, unchanged across the codebase: these alpha constants are written as light-theme RGB values, e.g. `rgba(15, 118, 110, 0.10)`, so in dark mode the wash is the light-theme hue under dark-theme text.)

## Typography

**Display Font:** Manrope (fallbacks: Segoe UI, Helvetica Neue, Arial) — declared as `--font-sans`
**Body Font:** Manrope (same stack)
**Label/Mono Font:** IBM Plex Mono (fallbacks: SFMono-Regular, Consolas) — declared as `--font-mono`

**Character:** Manrope's rounded geometric warmth keeps the admin panel friendly for non-accountants; IBM Plex Mono's typewriter voice makes every figure read as a ledger entry. The pairing is the paper-ledger metaphor carried into type.

> **Known gap (pre-existing):** neither webfont is actually loaded — there is no `@font-face`, no Google Fonts link, and no bundled font file in the repo. Users without Manrope / IBM Plex Mono installed locally see the fallback stacks. Adding font loading is the documented fix, not restyling.

### Hierarchy
- **Headline** (Manrope 700, 1.875rem/30px, tight tracking −0.025em): page titles in `PageHeader` only — one per page.
- **Title** (Manrope 700, 1.125rem/18px): card and section titles (`SectionCard`, `TableShell` headers); smaller strip titles run 14px/800.
- **Body** (Manrope 400–600, 14px; dense table cells 12.5–13px): UI copy and table prose. EN/ID mixed; sentence-case.
- **Label** (Manrope 700–800, 10.5–11px, uppercase, +0.08em tracking; sidebar section eyebrows push to +0.24em): column headers, toolbar field labels, bank codes, pill text. Pencil Gray.
- **Mono** (IBM Plex Mono 400–700, 11–12px): amounts, txn counts, dates, periods, result counts — every scanned numeral.

### Named Rules
**The Numerals-in-Plex Rule.** Any figure a clerk compares — debit, credit, count, date, period — sets in IBM Plex Mono. Prose never intrudes on the numeric voice.

**The Ledger-Label Rule.** Column headers and toolbar labels are 10.5–11px, bold-to-extrabold, uppercase, letter-spaced, Pencil Gray. They are the ledger's printed column captions.

## Layout

Single-column vertical stack inside an app shell: a fixed sidebar (StatementX wordmark, icon+label nav grouped under uppercase section eyebrows) and a scrollable content column. Pages compose as `PageHeader` (title, optional subtitle, right-aligned action slot) followed by full-width surface cards separated by a 16px rhythm (`space-y-4`; older surfaces use 24px).

Data surfaces standardize on the `TableShell` primitive — toolbar slot (filters + result count), scrolling table, footer slot (row counts) — so every ledger page shares skeleton and padding. Density is clerk-grade: table rows are 41–46px tall (`UploadSummaryView` fixes 46px), cell padding 10px, toolbar paddings compact at 10px 16px against the default 20px card padding.

Responsive behavior: at ≤1200px secondary table columns (Last Upload, Bank) drop out; at ≤1100px attention-queue issue rows reflow to a 2-column grid; at ≤900px toolbars stack vertically and issue rows collapse to one column. Tables keep `min-w-full` with horizontal scroll inside `TableShell`'s scroller.

## Elevation & Depth

A hybrid: tonal layering does the structural work, one soft ambient shadow does the atmosphere. Cards always carry `--shadow-card` (light `0 18px 40px rgba(55, 36, 18, 0.06)` — a warm-toned shadow; dark `0 18px 40px rgba(0, 0, 0, 0.28)`), so surfaces read as paper sheets lifted off the desk. In-card hierarchy is tonal, not elevated: muted fills for headers and chip rows, raised fills for inputs and editor pods. Depth never moves on tables — rows answer hover with a 4% teal tint while buttons and interactive cards translate up 1–2px and deepen to `--shadow-card-hover` (22px/48px blur).

### Shadow Vocabulary
- **Card rest** (`--shadow-card`, 0 18px 40px warm 6% / black 28%): every `surface-card`, dropdown panels, modals.
- **Card hover** (`--shadow-card-hover`, 0 22px 48px warm 10% / black 36%): `.interactive-card` hover only.
- **Soft** (`--shadow-soft`, 0 10px 24px ink 8% / black 24%): inputs, small floating pods (theme toggle, inline chip editors).
- **Primary glow** (0 12px 28px teal 22%): `btn-primary` only — the one colored shadow in the system.

### Named Rules
**The Rows-Tint-Cards-Lift Rule.** Table rows respond to hover with a background tint, never a shadow; buttons and cards may lift. A table that moves is a table that lies about being paper.

## Shapes

Rounded stationery, never sharp and never bubbly. Cards use 16px (`--radius-md`); large feature surfaces 24px (`--radius-lg`); inputs, buttons, and small controls 12px (`--radius-sm` / Tailwind `rounded-xl`) or 8–10px for tiny inline controls (icon buttons, assign buttons, chip-editor pods). Chips and pills close at 999px. Ruling is the signature: one device pixel of `--color-border` between every table cell, under every table header, and around every card — the "one-pixel hairline" discipline the system borrows from printed ledgers. Icons are Bootstrap Icons, 10–14px, colored by token, never outlined boxes around them.

## Components

### Buttons
- **Shape:** 12px radius, 8px 16px padding, Manrope 600.
- **Primary:** teal gradient (135deg primary → primary-strong) with teal glow shadow; hover lifts 1px and deepens the glow; disabled at 50% opacity. Used for the page's one main action.
- **Secondary:** cream raised fill, hairline border; hover strengthens border and lifts 1px. Carries most toolbar actions (Refresh).
- **Danger:** solid red with red glow; hover darkens toward `#a11818`. Delete confirmations only.
- **Ghost:** text-muted on transparent; hover gains muted fill. Low-stakes inline actions.
- **Focus:** `:focus-visible` = 2px solid `var(--color-primary-ring)` outline, 1px offset.

### Chips
- **Account chip** (pill, 999px): the per-row account status. Mapped = 10% teal tint, 22% teal border, Ledger Teal text; Unmapped/Mixed = 10% amber tint, 24% amber border, Annotation Amber text. Click opens an inline editor pod (raised fill, strong border, 10px radius, soft shadow) hosting a `SelectInput` or manual `TextInput` + apply button; a pencil glyph fades in on hover to advertise editability.
- **Group chip** (attention queue): 10px radius, muted fill, hairline border, amber or red 8px status dot, label, mono count, chevron; open state raises fill and border-strong.
- **Status/stat pills** (999px): muted fill pill for metadata; success variant uses the green tint formula for "all clear" states.

### Cards / Containers
- **Corner Style:** 16px (`surface-card`), 24px (`surface-hero`).
- **Background:** Ledger White; muted and raised fills layer inside.
- **Shadow Strategy:** `--shadow-card` at rest, always; see Elevation.
- **Border:** 1px `--color-border` everywhere; `--color-border-strong` on interactive hover.
- **Internal Padding:** 20px default card padding; compact toolbars 10px 16px.

### Inputs / Fields
- **Style:** raised fill, 1px border, 12px radius, 34px min height; optional leading icon in the shell variant.
- **Focus:** border turns teal plus a 4px `--color-primary-ring` glow (`0 0 0 4px`); dropdown panels are Ledger White cards with card shadow.
- **Error / Disabled:** disabled at 50% opacity with not-allowed cursor; errors surface via toast notifications and danger buttons rather than inline red fields.

### Navigation
- Fixed sidebar, Ledger-White-on-parchment; items are Manrope 600 with Bootstrap icons; active item gains a teal tint fill and teal text; section groupings set as 10px uppercase +0.24em pencil-gray eyebrows. Top of content carries a breadcrumb bar ("Admin Workspace / page name") with server status pill at right.

### Signature: The Attention Queue
`UploadAttentionQueue` — the needs-attention strip that leads a page when uploads need fixing: title + count pill + caption, group chips (amber/red dots, mono counts), and expanded issue rows (5-column grid: file, bank, meta, DB/CR amounts, inline select + Assign) that show the fix beside each problem. On a clean day it collapses to a one-line all-clear bar with a green check. Its counterpart, `UploadAccountChip`, makes account status a tappable pill with an inline editor pod. Together they express the system's story: exceptions first, archive below.

## Do's and Don'ts

### Do:
- **Do** take every color from the CSS variables in `admin_frontend/src/style.css` and add the dark variant in the `html.dark` block when introducing a token.
- **Do** set every numeral, date, and amount in IBM Plex Mono (`var(--font-mono)`), right-aligned in table columns.
- **Do** build data surfaces on the `TableShell` / `SectionCard` / `PageHeader` primitives, with hairline 1px `--color-border` ruling and 41–46px rows.
- **Do** express status as tint chips: ~10% alpha fill, ~22–24% alpha border, solid token text.
- **Do** use `:focus-visible` with `2px solid var(--color-primary-ring)` outline (1px offset) on all custom controls, and honor `prefers-reduced-motion` for transitions.
- **Do** write micro-labels as 10.5–11px bold uppercase with 0.08em tracking in Pencil Gray.

### Don't:
- **Don't** hardcode hex values or raw Tailwind palette classes (`text-red-500`) in components — the token layer is the only source.
- **Don't** use red for anything that is not destructive, and don't use amber for success — amber is a pending decision, red is a destroyed row.
- **Don't** put shadows or lifts on table rows; rows tint (4% teal), cards lift.
- **Don't** invent a second accent or introduce solid-fill status colors — the tint-not-fill formula and the teal/amber/red division are the system.
- **Don't** drop below ~10.5px for labels (the incumbent 9–10px table text is a known accessibility failure being corrected, not a precedent).
