---
version: 1
slug: "admin-frontend-src-views-reportsview-vue"
primary_target: "admin_frontend/src/views/ReportsView.vue"
related_targets: ["admin_frontend/src/components/reports/ReportFilters.vue","admin_frontend/src/components/reports/PayrollSalarySummary.vue"]
---

# Surface Brief: Financial Reports (ReportsView.vue)

- **Mode:** Operate — the visitor completes the task of generating, reading, and exporting financial reports.
- **Primary target:** `admin_frontend/src/views/ReportsView.vue`
- **Related targets:**
  - `admin_frontend/src/components/reports/ReportFilters.vue`
  - `admin_frontend/src/components/reports/PayrollSalarySummary.vue`
  - `admin_frontend/src/components/payroll/PayrollEmployeeCell.vue` (shared with History's PayrollSalaryHandling)
  - `admin_frontend/src/components/payroll/PayrollComponentChip.vue` (shared with History's PayrollSalaryHandling)

## Concept: one instrument panel

The analysis shell is a single ruled surface that leads into the report sheet:

1. `PageHeader` — title "Financial Reports", subtitle, actions: Export (primary, only when the active tab supports it). General Ledger lives in the sidebar REPORTS section (it is a page, not a report tab); do not put a GL button back in this header.
2. One `SectionCard` (`p-0`) holding three bands separated by hairlines:
   - **Tab strip** — six report tabs via the shared `components/ui/PillTabs.vue` (pill/capsule language adopted SYSTEM-WIDE: Reports, HistoryView, SettingsView all use PillTabs; the file was renamed from an underline `TabRail.vue` experiment). **Decision history — do not flip again:** underline was tried twice (standalone, then system-wide) and the owner rejected it both times after seeing it in situ: pills fit the paper-ledger card/chip vocabulary, underline did not. Active pill = 12% teal tint + 18% teal border + soft shadow; `role="tablist"/"tab"` + `aria-selected`, roving-tabindex Arrow/Home/End keyboard navigation. Horizontal scroll on narrow viewports. Navigation away (General Ledger) is NOT a tab; it lives in the sidebar (see `config/navigation.js`).
   - **Filter band** — `ReportFilters` renders six inline fields (Report Type, Year, Period Start/End, As of Date, Company) with flex-wrap; right-aligned ledger-label status readout: "⚡ AUTO REFRESH" at rest, spinning "UPDATING…" while regenerating.
   - **Error strip** — slim danger-tint row inside the shell (icon + message + Retry ghost button), only when `store.error`.
3. Content area — `min-h-[400px]`; frosted loading overlay ("Generating reports…") over the report component; report content renders below the shell.

## Invariants

- All colors via CSS variables; alpha tints written as light-theme RGB (system-wide known quirk).
- Numerals/dates in IBM Plex Mono; labels are 10.5–11px bold uppercase +0.08em Pencil Gray.
- Report components (IncomeStatementComparative, BalanceSheet, …) keep their incumbent look; a full token cleanup of their raw Tailwind palette classes is a documented follow-up.
- `refreshKey` force-remount per generation; filters persist server-side and auto-regenerate on change (300ms debounce).
- PayrollSalarySummary month headers omit the year when the period stays within one calendar year (the period line above carries it); keep the year when the range spans multiple years.
- Sticky table cells must use opaque token backgrounds (`bg-surface`, `bg-surface-muted`) — translucent tints let scrolled content bleed through.
- Payroll employee identity rows and salary-component chips come from the shared `components/payroll/` primitives (`PayrollEmployeeCell`, `PayrollComponentChip`) — do not fork new markup in either view.

## Verified

- Light + dark at 1440px, narrow 900px (tabs scroll, filters wrap, status stays aligned).
- Payroll tab shows employee names with IDs as sublabels after the backend name-resolution fix.
- Payroll table scrolled 600px with expanded rows: no bleed-through under sticky cells; month headers year-free on single-year periods.
