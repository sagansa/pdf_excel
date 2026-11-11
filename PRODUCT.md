# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

StatementX is operated by a mix (user-confirmed): the Sagansa internal team, finance/accounting staff at client companies, and the owner-operator personally. Skill levels vary, and some users are not accountants by training, so the interface must stay self-explanatory. Primary situation: bookkeeping administration — turning bank statement activity into classified, mapped, report-ready accounting data.

## Product Purpose

StatementX is an internal admin panel that ingests bank statements (email ingestion + bank parsers), normalizes transactions, classifies them via user-defined "marks" (classification rules), maps marks to a chart of accounts, and produces financial reports in two reporting lenses: "Real" (internal management reporting) and "Coretax" (Indonesian tax/DJP reporting — interpretation inferred from code; `report_type` real/coretax is code-evidenced). It also covers HRD presences, HPP (cost-of-goods batches), multi-company management, trial balance, general ledger, and balance-continuity checks.

## Positioning

Statement-in to journal-out: automated ingestion plus mark-based classification with AI suggestion levels (rule engine, ML, LLM) feeding a low-confidence review queue — bookkeeping throughput that manual entry tools cannot match. The dual Real/Coretax mapping on a single rule is the mechanism a generic expense tracker could not truthfully copy.

## Operating Context

Indonesian SME bookkeeping. UI copy mixes English and Indonesian. "Coretax" refers to Indonesia's tax administration reporting; fiscal categories (DEDUCTIBLE / NON_DEDUCTIBLE / NON_TAXABLE_INCOME) drive tax treatment. Runs as a Flask API + Vue SPA, dev via `npm run dev` (admin_frontend) and `python3 server.py` (admin_backend).

## Capabilities and Constraints

- Marks data model (must keep): `internal_report`, `personal_use` names; boolean flags `is_coretax`, `is_asset`, `is_service`, `is_salary_component`, `is_rental` (inline-togglable); `fiscal_category`; COA mappings split by report_type (`real` / `coretax`), each with DEBIT/CR direction. Some marks are intentionally left unmapped (user-confirmed) — unmapped is a neutral informational state, not a warning.
- Marks feed transaction classification, financial reports, and the AI review queue; the AI description-enrichment pipeline (rule + LLM) feeds rule matching.
- Backend API and data model are fixed for the marks redesign (user-confirmed); the redesign is frontend, but interaction patterns may be rethought — user explicitly wants the frontend refactored into reusable components.
- Multi-company: one deployment serves several companies.

## Brand Commitments

- Product name "StatementX" (sidebar wordmark).
- Established visual world in code: warm paper-ledger light theme (`#f3ede3` ground, `#fffdf8` surfaces, teal primary `#0f766e`, amber accent `#b45309`), dark variant, Manrope + IBM Plex Mono, CSS-variable tokens, Bootstrap Icons, 12–24px radii, soft shadows.

## Evidence on Hand

- Full working app in repo: `admin_frontend` (Vue 3 + Vite + Tailwind + Pinia), `admin_backend` (Flask).
- `AI_RECOMMENDATIONS.md`, `PRD_AI_FEATURES.md` document the AI classification roadmap (rule/ML/LLM levels, confidence, review queue).
- `review_2025_artifacts/` holds 2025 review data (untracked).

## Product Principles

1. Function survives the redesign: every current capability of a surface keeps working, only its form may change.
2. Design for the least expert user in the mix; scanability and self-explanation beat density.
3. Make downstream impact visible: a rule editor should show what a mark affects before the user commits.
4. Build reusable components, not one-off page code (user-requested).

## Accessibility & Inclusion

Mixed-skill users including non-accountants; UI language mixes English and Indonesian. Standard web accessibility (keyboard, focus, contrast in both themes) applies; small 9–10px text in the incumbent table is a known failure to correct.
