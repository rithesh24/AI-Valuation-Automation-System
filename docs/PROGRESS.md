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

## Phase 2 - File Upload System, backend (2026-07-23)

- Implemented `upload_service.py`: `UploadCategory` enum (property_document / template / supporting_image) with per-category allowed extensions, filename sanitization, chunked streaming to disk with enforced max-size limit, and session-based grouping (UUID) so files belonging to the same report land under `data/uploads/{session_id}/{category}/`.
- Added `POST /uploads` route (`app/api/routes/uploads.py`) — thin adapter over `upload_service.py`; validation failures return HTTP 400 with a clear message.
- Added `UPLOAD_DIR` and `MAX_UPLOAD_SIZE_MB` settings (`.env`-configurable, defaults `data/uploads` / 25 MB).
- Added `python-multipart` dependency (required by FastAPI to parse multipart file uploads).
- Added `backend/data/` to `.gitignore` (uploaded files must never be committed).
- Added `tests/test_uploads.py`: valid upload, disallowed extension rejection, oversized file rejection, session grouping across calls. All 5 backend tests pass (`pytest`).
- Frontend upload screen (Next.js) not yet started — next step for Phase 2.

## Phase 2 - File Upload System, frontend (2026-07-23)

- Added `lib/api.ts`: typed `uploadFiles()` wrapper posting `FormData` to the backend's `POST /uploads`, base URL from `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).
- Added `components/FileUploadSection.tsx`: reusable upload UI (file picker restricted to the category's allowed extensions, upload list, inline error display).
- Replaced the placeholder home page with three sections — Property Documents, Bank Valuation Template, Supporting Images (optional) — sharing one `sessionId` in page state so files from all three land in the same backend session folder.
- Verified live (not just `next build`): ran the backend (`uvicorn`) and frontend (`next dev`) together, confirmed the page renders all three sections server-side, and sent a real cross-origin upload request matching what the browser's `fetch` would send — confirmed CORS headers, a 200 response, and the file landing on disk at `data/uploads/{session_id}/property_document/...`. No in-browser click-through was possible in this environment (no browser-automation tool available), so manual visual/UX testing in an actual browser is still recommended before considering the screen final.
- Phase 2 (File Upload System) is now complete — all items checked off in `docs/ROADMAP.md`.
