# AVAS Progress Log

## Phase 1 - Project Foundation (2026-07-22)

- Initialized a project-scoped Git repository (the pre-existing repo at the home directory root was left untouched).
- Scaffolded the Electron shell (TypeScript, minimal main/preload processes, no business logic per ARCHITECTURE.md).
- Scaffolded the Next.js frontend (TypeScript, App Router, static export configured for Electron packaging).
- Scaffolded the FastAPI backend: service module skeletons for each responsibility named in ARCHITECTURE.md (`upload_service`, `document_parser`, `easr_service`, `prompt_builder`, `claude_service`, `report_service`, `usage_service`), config/logging setup, and a `/health` endpoint.
- Added the pytest scaffold with a first passing test against `/health`.
- Installed root/frontend/electron npm dependencies (396 packages; 6 audit vulnerabilities flagged, not yet addressed).
- Verified the frontend builds cleanly (`next build`, static export, type-checked, 4 pages generated).
- Verified the Electron shell compiles cleanly (`tsc -p tsconfig.json`).
- Verified the backend runs (`.venv` created, dependencies installed, `pytest` passes).
- Phase 1 (Project Foundation) is complete — all items checked off in `docs/ROADMAP.md`.

## Architecture & Planning (2026-07-22)

- Reviewed the client's current working Claude prompt (`docs/PROMPTS.md`) against the project architecture. Confirmed strong alignment on non-fabrication rules, and identified it as the source for the canonical data schema (Sections 4-11, 24-26).
- Decided the report-generation strategy: a three-stage pipeline (extraction → Claude-assisted template mapping → deterministic clone-and-fill injection), with the mapping result cached by a hash of the template's extracted structural skeleton. See `docs/DECISIONS.md` (D5, D6, D9).
- Confirmed with the client that the Maharashtra eASR portal has no CAPTCHA — full unattended Playwright automation is in scope (D7).
- Decided a two-tier market-research strategy: official/government sources via dedicated Playwright services (Tier 1), comparable listings via Anthropic's hosted web-search tool through the Claude API (Tier 2) — avoids building fragile/ToS-risky scrapers for real-estate portals (D8).
- Updated `docs/ARCHITECTURE.md` (service responsibilities, persistence layer, data flow) and `docs/ROADMAP.md` (Phases 4-6) to reflect these decisions. Full rationale recorded in `docs/DECISIONS.md`.
- No implementation started yet for Phases 2-6 — this was architecture/planning only.
- Created `docs/UPDATED_PROMPTS.md`: adapted the client's working prompt (`docs/PROMPTS.md`) into the three-stage pipeline (D5). Stage 1 (Extraction) reuses ~all of the original prompt's domain content (field lists, valuation logic, non-fabrication rules) restructured for structured-JSON output instead of a Word document; visual-formatting instructions were dropped (formatting fidelity is now Stage 3's job) while content-formatting rules (Indian numbering, figures + words) were kept. Stage 2 (Mapping) is a new prompt authored from scratch — it has no equivalent in the client's current workflow. Stage 3 (Injection) has no prompt; it's pure `python-docx` code. The eASR "Survey Prompt" was converted into deterministic Playwright automation parameters rather than an LLM prompt.
