---
version: 1
slug: "admin-frontend-src-views-hrdview-vue"
primary_target: "admin_frontend/src/views/HrdView.vue"
related_targets: ["admin_frontend/src/components/hrd/PresencesPanel.vue"]
---

# Surface Brief: HRD Presences (HrdView.vue)

## Scope and visitor mode

Operate. Route `/hrd` in the StatementX admin panel: HRD/bookkeeping staff monitoring employee
presences synced from the Sagansa presence API. Primary target `admin_frontend/src/views/HrdView.vue`;
related target `admin_frontend/src/components/hrd/PresencesPanel.vue` (moved from
`components/history/PayrollPresencesTable.vue`).

## Audience, job, actions, constraints

- Audience: mixed-skill internal staff (HRD + bookkeeping), some non-accountants; EN/ID mixed copy.
- Job: pull presence records from the Sagansa presence API into the local DB, filter per
  company/period, scan attendance rows.
- Actions that must survive: filter by company/year/month, search, reload, Sync API
  (with optional API URL/token override + localStorage token cache), row table
  (creator, store, shift name/start/end/duration, check-in/out, created, updated).
- Constraints: backend API fixed (`/api/payroll/presences` list+sync, limit 500); Employees and
  Requests tabs remain visible placeholders (SegmentedControl); new stats strip approved by user
  (records, unique employees, check-in date range). Dark theme must work (tokens only).

## Chosen direction and memorable moment

Extension of the established Warm Paper Ledger world — no new identity. The surface becomes the
system-standard data page: PageHeader (Sync = the page's one primary action) → SegmentedControl
tabs → StatCard strip (the ledger's day summary) → TableShell with a compact filter toolbar
(labeled selects, mono result count) and a hairline-ruled attendance table where each row reads
like a timebook entry: name over store, shift with mono hours, mono timestamps.

## Unresolved decisions

None — scope (whole page), tabs (SegmentedControl), and stats strip approved by the user
2026-11-15.

## Direction contract

THESIS: The presence log is a timebook — one row per clock-in, scanned the way a clerk scans a
shift ledger — refusing the generic admin "filter card + white table + indigo accents" arrangement
the page shipped with.

OWN-WORLD: Warm paper ledger tokens only (parchment ground, ledger-white shell, teal primary,
amber pending, mono numerals); no hardcoded palette classes; TableShell hairline ruling; tint
chips for states; Manrope voice, IBM Plex Mono for every timestamp, count, and hour figure.

STORY: The visitor sees at a glance how much presence data is loaded (records, employees,
date range), can narrow it by company and period without leaving the page, and pulls fresh data
with one committed Sync action; sync results and failures report as toasts, empty states explain
the recovery.

FIRST VIEWPORT: PageHeader (title "HRD Presences", one-line subtitle, right-aligned Reload
secondary + Sync API primary) → SegmentedControl (Presences/Employees/Requests with icons) →
three StatCards (Records · Employees · Period) → TableShell opening with its toolbar (Company,
Year, Month labeled selects, search field, mono "N of max 500" count) and the first ~8 attendance
rows.

FORM: System-standard data-surface composition (PageHeader → controls → stats → TableShell),
position 1 of the ordered list for an Operate surface inside an established world; no
concept-seed roll was dealt because this is a local extension of an established world, not a
genuinely open whole surface (new-work §3). seed: none (unavailable)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
verdict, DESIGN.md, and every shipping raster carrying its provenance
