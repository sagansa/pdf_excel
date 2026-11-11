# Surface Brief — Marks (Transaction classification rules)

Scope: `admin_frontend/src/views/MarksView.vue` + its `components/marks/*` modals. Mode: **Operate** (admin manages classification rules; scan, find, verify mapping coverage, edit safely).

Audience/job: mixed-skill users (Sagansa team, client finance staff, owner) maintaining marks: check coverage, toggle flags, keep Real/Coretax COA mappings complete.

Constraints (user-confirmed): keep the app's established visual world; keep inline flag toggling, modal-based editing, and the data model/API; frontend refactor toward reusable components. Fix: wall of columns, no search/filter, cramped COA mapping cell, unclear downstream impact.

## Direction contract

THESIS: One rule = one quiet summary row that opens in place into its full sheet; the 10-column wall collapses into a compact row plus a detail band, refusing the everything-visible-at-once default.

OWN-WORLD: The app's incumbent paper-ledger system — cream ground, `#fffdf8` surface cards, teal `#0f766e` primary, amber `#b45309` warnings, Manrope + IBM Plex Mono, hairline `#d9cfbe` dividers, 12–16px radii. No new palette or material.

STORY: The operator scans names, trait chips and coverage dots to find a rule; searching/filtering (unmapped, flag, fiscal) narrows the list; expanding a row reveals flags as switches, fiscal category, and Real/Coretax mappings side by side; coverage and unmapped counts lead the header.

FIRST VIEWPORT: Page header (eyebrow, title, "Add New Mark") with coverage chips (8 marks · 1 unmapped · Real 7/8 · Coretax 6/8); toolbar with search + filter chips; compact table of rows; one row expanded showing the detail band (flags row, fiscal select, Real/Coretax mapping groups side by side, Manage COA + Edit/Delete).

FORM: Expandable Rule Rows — dealt candidate #2 of the surface roll (seed:47033cff8988e007); locked on the decision page (option `expandable-rows`). Signature interaction: the in-place expansion band with side-by-side Real/Coretax mapping groups; coverage dots summarize each lens per row.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
