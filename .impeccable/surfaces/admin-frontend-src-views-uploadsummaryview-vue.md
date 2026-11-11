---
version: 1
slug: "admin-frontend-src-views-uploadsummaryview-vue"
primary_target: "admin_frontend/src/views/UploadSummaryView.vue"
related_targets: []
---

# Surface: Upload Summary (`admin_frontend/src/views/UploadSummaryView.vue`)

## Scope and visitor mode
Operate. Route `/upload-summary`. Audience: mixed-skill bookkeeping staff (some non-accountants), Indonesian SME context, EN/ID mixed copy. Jobs (user-confirmed, all four): audit uploads, fix account mapping, cleanup/re-upload, ingestion overview.

## Chosen direction
"Triage Queue" — position 3 of 7 grounded structural candidates (1 ledger-first+aggregate strip, 2 bank-grouped ledger, 3 triage queue ← dealt lead locked by user, 4 period-coverage matrix, 5 master-detail, 6 ingestion-health dashboard, 7 full-bleed workbench grid). Memorable moment: the needs-attention strip that collapses to a slim all-clear bar on a clean day. Signature discipline borrowed from declined challenger (reference-setting): one-device-pixel hairline ruling. Unresolved decisions: none.

## Direction contract
THESIS: The page leads with what needs fixing — unmapped, mixed, unusual files — each with its fix inline; the ledger below is the archive, not the worklist. It refuses the category default of an undifferentiated 8-column dump where exceptions hide row by row.

OWN-WORLD: The established StatementX paper-ledger system, unchanged: CSS-variable tokens (light warm-paper + dark variants), surface cards at 16px radius with hairline borders, Manrope UI voice + IBM Plex Mono for numerals/dates, teal for mapped/confirm, amber for unmapped/mixed flags, red for destructive, status chips, ~46px table rows, soft shadows.

STORY: On arrival the bookkeeper sees today's exceptions and fixes them without hunting; the archive answers "what is in the database, per bank and period" with one-line periods, readable amounts, and per-row account status. Nothing about the data model changes.

FIRST VIEWPORT: Header (eyebrow, title, subtitle, Refresh) → attention strip (count badge, group chips per issue class, expanded group's issue rows with inline select + Assign) → compact filter row (bank, year, filename search, result count) → dense archive ledger: File / Bank / Account chip / Txns / one-line Period / Debit / Credit / Last upload / delete, amber left rule on flagged rows.

FORM: "Triage Queue", position 3 of the ordered grounded list, dealt lead locked on the decision page. SEED REFERENCE: seed:9a7f6578c5bac27e.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
