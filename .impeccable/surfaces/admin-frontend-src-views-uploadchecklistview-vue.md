---
version: 1
slug: "admin-frontend-src-views-uploadchecklistview-vue"
primary_target: "admin_frontend/src/views/UploadChecklistView.vue"
related_targets: []
---

# Surface: Upload Checklist (Yearly upload status per bank account)

- **Target:** `admin_frontend/src/views/UploadChecklistView.vue` + `admin_frontend/src/components/uploads/BankAccountDefinitionsCard.vue`
- **Mode:** Operate. Visitor: Sagansa team + client finance staff (mixed skill, some non-accountants), Indonesian SME bookkeeping context, EN/ID copy.
- **Job:** equally — track year completeness, find & close missing bank×month gaps, audit DB/CR data quality. Secondary: define/edit bank accounts.
- **Content/proof:** per-year API `upload-checklist` returns all 12 months × bank columns (key/label/bank_code/account_number/display_name), cells with uploaded/txn/DB/CR/source_files/last_upload; future months arrive as uploaded:false (frontend derives "belum jatuh tempo" client-side).
- **Constraints:** frontend-only; fixed API; established paper-ledger world (tokens in `src/style.css`, Manrope + IBM Plex Mono, Bootstrap Icons); bank filter semantics (empty set = all, last-visible click clears); imbalance flag >30% delta; year range 2020..currentYear+1; loading/error/empty states; no 9–10px content text.
- **Chosen direction:** "Twelve Columns" — kalender tahun (dealt lead, surface round, code-led). Memorable moment: the year slot bar's staggered fill on load — the whole year's completeness reads as one rhythm.
- **Unresolved:** none.

## Direction contract

THESIS: The year reads as a wall calendar — 12 month columns, each bank owning one slot per month — so full/empty rhythm, gaps, and imbalance are geometry you see, not numbers you compare; it refuses the incumbent's amounts-in-every-cell matrix that drowned completeness in data.

OWN-WORLD: Incumbent paper-ledger tokens only — `#f3ede3` ground, `#fffdf8` surfaces, teal `--color-primary` for uploaded, `--color-danger` for gaps, `--color-accent` amber for imbalance, muted border tone for not-yet-due; IBM Plex Mono for every figure; Manrope for labels; Bootstrap Icons; 12–16px radii; soft `--shadow-card` depth on the two big cards only.

STORY: In five seconds the finance staff sees the year's fill rhythm and which bank is bleeding months; hovering a slot tells them the file, txn count and totals; the rail tells each bank's n/12 and year totals; clicking a rail card isolates that bank across the grid; the queue of what to chase is the pattern of red slots by month.

FIRST VIEWPORT: PageHeader shell (year select + refresh, unchanged app convention) → year progress card: big mono %, caption n/36 slot, 36-segment fill bar grouped by month with legend (Terupload / Bolong / Selisih / Belum jatuh tempo), year DB/CR totals right → main row: 250px rail of per-bank cards (name, masked account, 12-cell mini strip, n/12, txn, DB/CR, state label, focus-click) + "Kelola akun bank" link → month grid card: 12 columns, NOW column ringed teal, cells ~66px (uploaded: bank tag, txn, compact DB/CR, ⚠ flag; missing: dashed danger slot with !; future: muted) → collapsed "Kelola Akun Bank" bar.

FORM: "Twelve Columns", ranked 5 of my 7 grounded structures; SEED REFERENCE: seed:0cdba7030d6f63a9. Signature interaction: staggered slot-bar fill on data load (320ms per slot, 12ms stagger, disabled under prefers-reduced-motion). Bank definitions card redesigned as collapsed manager (summary header, expandable form + definitions list + unmapped candidates), reachable from the rail link.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
