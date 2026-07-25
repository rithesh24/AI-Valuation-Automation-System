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

## Phase 3 - Document Processing (2026-07-24)

- Implemented `document_parser.py`: `extract_pdf_text()` (PyMuPDF, page-by-page), `extract_docx_text()` (python-docx, paragraphs + table cells in document order), `ocr_scanned_document()` (pytesseract, handles both PDFs — rendered page-by-page — and direct image files).
- Implemented the OCR trigger rule from D11: a PDF page with under 20 characters of extracted text is treated as scanned and OCR'd automatically, so mixed text/scanned PDFs are handled transparently within a single `extract_pdf_text()` call.
- Added `DocumentParserError` for unreadable/corrupt files and a missing-Tesseract-binary case, following the same fail-clearly pattern as `UploadValidationError` in `upload_service.py`.
- Added `TESSERACT_CMD` (optional Tesseract binary path override) and `OCR_TRIGGER_CHAR_THRESHOLD` settings to `app/core/config.py`.
- Added dependencies: PyMuPDF, python-docx, pytesseract, Pillow (`backend/requirements.txt`).
- Added `backend/tests/test_document_parser.py` — fixtures (PDF, DOCX, scanned-image PDF, direct image) are generated programmatically in the test file rather than committed as binary files, to keep the repo diff-friendly. OCR-dependent tests skip gracefully if Tesseract isn't installed on the machine running the suite. All 12 backend tests pass (`pytest`).
- Phase 3 (Document Processing) is now complete — all items checked off in `docs/ROADMAP.md`.
- Not yet addressed: packaging Tesseract with the Electron installer (deferred to Phase 9), per D13.

## Phase 4 - Browser Automation (2026-07-24)

- Implemented `easr_service.py`: Playwright-driven automation of the real Maharashtra eASR 1.9 portal (District via URL param → Taluka/Village cascading dropdowns → generic result-table parsing that handles both the rural Assessment-Type/Range shape and the urban Sub-Division/Attribute grid shape, since which one appears depends on the village, not the district). Selectors were discovered by actually driving the live portal with Playwright (screenshots + DOM dumps), not guessed.
- `EASRGuidelineResult` uses a generic `columns`/`rows` schema rather than a fixed set of fields, since the two table shapes are genuinely different (see D14) — this superseded the fixed-schema model from the original Phase 4 plan once live testing showed why it wouldn't fit rural villages.
- Implemented the retry contract from `docs/ARCHITECTURE.md`: 3 total attempts on transient Playwright failures, immediate fail (no retry) on bad input / missing Chromium / unrecognized district, via `EASRServiceError`.
- Verified end-to-end against the live portal (not mocked): a rural village lookup, an urban village lookup filtered by a real survey number (confirmed the returned row's rates match what's shown on the actual portal page), and an invalid-district case failing fast with a clear message. Also smoke-tested through the actual HTTP layer (`POST /easr/lookup` returned 200 with correct data).
- Added `backend/app/api/routes/easr.py` (`POST /easr/lookup`) as a disposable manual-testing endpoint, registered in `app/main.py` — not part of the documented architecture; Phase 5/6's `report_service.py` will be the real caller.
- Added `backend/tests/test_easr_service.py`: model validation tests, retry-loop tests (fake `_run_search`, no real browser), and real-Chromium table-parsing tests against local HTML fixtures (not the live site) — gated by a `requires_playwright_browsers` skip marker matching the `requires_tesseract` pattern from Phase 3. All 20 backend tests pass (`pytest`).
- Added `playwright` dependency + `EASR_*` settings (`app/core/config.py`, `.env.example`) + the `playwright install chromium` post-install step (`README.md`).
- Recorded known V1 gaps (district-identifier coverage, single-page survey-number search, unverified "no data" state) in `docs/DECISIONS.md` D14 rather than leaving them undocumented.
- Phase 4 (Browser Automation) is complete except the explicit stretch goal (RERA/SRO feasibility, not attempted) — remaining items checked off in `docs/ROADMAP.md`.
- Follow-up same day: evaluated the RERA/SRO stretch item live. MahaRERA's project search (`maharera.maharashtra.gov.in/projects-search-result`) has no CAPTCHA and is feasible to automate the same way as eASR. SRO/Index-II document search requires a CAPTCHA on every search and is not feasible for unattended automation. See `docs/DECISIONS.md` D15.
- Same day, built on the RERA finding: implemented `official_sources_service.py` (`RERAService`) — searches MahaRERA's registered-projects listing by project name/registration number, district, and/or pincode, mirroring `easr_service.py`'s conventions (per-call browser lifecycle, same retry contract, generic result philosophy). Result cards are parsed by adjacent-label text rather than positional selectors, since the portal's markup doesn't cleanly wrap label/value pairs.
- Verified end-to-end against the live portal (not mocked): search by project name (exact field match confirmed against the real page), search by district (10 of 12,740 results returned, first page only — a documented V1 limit), a genuine zero-match search (`found=False`, no crash), and a no-filter-given case failing fast with a clear message.
- Added `backend/app/api/routes/rera.py` (`POST /rera/lookup`) as the same kind of disposable debug route as `/easr/lookup`, registered in `app/main.py`.
- Added `backend/tests/test_official_sources_service.py`: model tests, pure text-parsing tests against a real captured result card (no browser), and retry-loop tests (fake `_run_search`). All 27 backend tests pass (`pytest`).
- Recorded the implementation and its known V1 gaps (first-page-only results for broad searches) in `docs/DECISIONS.md` D16. All Phase 4 roadmap items, including both stretch sub-items, are now checked off.

## Phase 5 - AI Integration (2026-07-25)

- Implemented the canonical data schema (`backend/app/models/valuation_schema.py`, D9): nested Pydantic models covering documents referred to, property identification, ownership/title flow, area reconciliation, boundaries, site/building particulars, statutory position, encumbrances, purpose/basis, highest-and-best-use, approach selection, Tier 1/Tier 2 market research, comparable evidence, all four valuation calculation methods, reconciliation/concluded values, red flags, and limiting conditions.
- Sourced fields from `docs/UPDATED_PROMPTS.md` Stage 1 (sections 2-20) rather than the raw client prompt (`docs/PROMPTS.md`), since UPDATED_PROMPTS.md is the version already adapted for structured-JSON output per the three-stage pipeline (D5).
- Every leaf field is a plain string defaulting to the non-fabrication sentinel (`INFO_NOT_AVAILABLE`), so "unavailable" is representable the same way real data is, and Stage 3 injection can always write `.text` directly without null-handling.
- Added `canonical_schema_field_list()`: flattens the nested schema into (dotted name, description) pairs, marking repeating structures with `[]` — feeds Stage 2's mapping prompt (`{{canonical_schema_field_list}}`) directly, no separate hand-maintained list.
- Added `backend/tests/test_valuation_schema.py` (4 tests: sentinel defaults, JSON serialization, field-list flattening, repeating-structure marking). Full backend suite: 31/31 passing.
- Not yet done: wiring this schema into `prompt_builder.py` / `claude_service.py` (next Phase 5 item).

- Implemented `PromptBuilder.build_extraction_prompt()` (`backend/app/services/prompt_builder.py`): assembles the Stage 1 (Extraction) prompt verbatim from `docs/UPDATED_PROMPTS.md` (not the raw client prompt), substituting valuation date, Tier 1 official-data text, extracted document texts, and the canonical schema's JSON Schema (via Pydantic's `model_json_schema()`) as the output-format contract. No API calls in this module, per ARCHITECTURE.md.
- Implemented `ClaudeService.extract_valuation_data()` (`backend/app/services/claude_service.py`): sends the Stage 1 prompt to the Anthropic Messages API with the hosted web-search tool attached (D8 Tier 2), parses the JSON response into a `ValuationReportData`, and returns it alongside input/output token counts. Retry contract mirrors `easr_service.py`: transient errors (`APIConnectionError`, `RateLimitError`, `InternalServerError`) retry up to `ANTHROPIC_MAX_RETRIES`; other API errors (auth, bad request) and malformed/schema-invalid JSON responses fail immediately via `ClaudeServiceError`.
- Added `ANTHROPIC_MODEL`, `ANTHROPIC_MAX_RETRIES`, `ANTHROPIC_RETRY_DELAY_SECONDS` settings (`app/core/config.py`, `.env.example`), and the `anthropic` SDK dependency (`requirements.txt`).
- No `ANTHROPIC_API_KEY` is set yet (client will add it later) — `extract_valuation_data()` raises a clear `ClaudeServiceError` if called without one, rather than the app failing to start or crashing elsewhere; nothing else in this step requires a live key, since tests fake `ClaudeService._call_claude` the same way `easr_service.py`'s tests fake `_run_search`.
- Added `backend/tests/test_prompt_builder.py` (6 tests) and `backend/tests/test_claude_service.py` (6 tests, incl. retry, non-retryable short-circuit, malformed JSON, code-fence stripping). Full backend suite: 43/43 passing.
- Not yet done: `usage_service.py` (Token tracking — persisted cost/monthly usage) is still a stub; `extract_valuation_data()` returns token counts but doesn't record them yet. Stage 2 (template mapping) prompt is not built — it depends on the Phase 6 template-skeleton extractor, which doesn't exist yet.
- Discussed Token tracking (the last unfinished Phase 5 item) and proposed an implementation (stdlib-`sqlite3`-based `usage_service.py`, wired into `claude_service.py`). Client decided to defer it to a later session — `usage_service.py` remains a stub. See `docs/DECISIONS.md` D17.

## Phase 6 - Report Generation (2026-07-25)

- Implemented `ReportService.extract_template_skeleton()` (`backend/app/services/report_service.py`, D5/D6): parses an uploaded `.docx` template with `python-docx`, walking the document body's paragraphs and tables in actual XML document order (python-docx's `.paragraphs`/`.tables` are separate and unordered relative to each other, so this uses the standard body-iteration recipe). Each location (paragraph or table cell) gets a stable `location_id`, its own text, and a `context` list carrying the "nearby label text" signal `docs/ARCHITECTURE.md` calls for: the previous non-blank paragraph for a paragraph location, or every other cell in the same row for a table-cell location.
- Added `ReportService.skeleton_hash()` — hashes the extracted skeleton for the Stage 2 mapping cache key (D6). Only the hash function is built; the SQLite cache table/lookup itself is a separate, not-yet-built roadmap item.
- Known scope limits (not attempted, not silently broken): headers/footers and nested tables aren't walked — uncommon in bank valuation templates, deferred until a real template needs it.
- Added `backend/tests/test_report_service.py` (7 tests: paragraph ordering, blank-paragraph context, table-row context, unique location IDs, missing-file error, hash stability/change-detection). Full backend suite: 50/50 passing.
- Not yet done: the Claude-assisted mapping call (feeds this skeleton + `canonical_schema_field_list()` to `claude_service.py`), the SQLite mapping cache, clone-and-fill injection, quality-check pass, preview, and download — remaining Phase 6 items.
- Implemented `ClaudeService.map_template_fields()` (Stage 2): sends the Stage 2 prompt (`PromptBuilder.build_mapping_prompt()`, new, verbatim from `docs/UPDATED_PROMPTS.md`) built from `canonical_schema_field_list()` + the extracted skeleton, with no web-search tool attached (a structural-matching task, not research). Refactored the retry logic shared with `extract_valuation_data()` into a private `_send_with_retries()` helper rather than duplicating it. `canonical_schema_field_list()`'s existing `[]`-suffixed dotted names (e.g. `comparable_evidence[].location`) already give per-column granularity for repeating tables, so no separate column-mapping response format was needed from Claude.
- Added the SQLite mapping cache (D6): `app/core/db.py` (minimal stdlib `sqlite3` connection helper, no ORM) + a `template_mapping_cache` table keyed by skeleton hash. `ReportService.get_or_create_mapping()` checks the cache first and only calls Claude on a miss or an explicit `force_regenerate` override; a template's `first_seen_at` date is preserved across regenerations.
- Implemented Stage 3 (`ReportService.inject_data()`): scalar fields have the existing Run's text mutated in place; repeating groups (comparable evidence, flow of title, etc.) get their prototype table row's XML cloned once per extra item, using the column position already encoded in each subfield's mapped location — sandbox-verified before writing the real implementation that `run.text = value` preserves formatting (bold, font) while `cell.text = value` silently destroys it, so injection only ever uses the former.
- Added `run_quality_check()`: flags scalar fields that hold a real value but have no usable mapped location (`injection_failures`) separately from fields honestly marked unavailable (`disclosed_unavailable`, not a failure) — the "no placeholder/empty fields left behind" check from `docs/ARCHITECTURE.md`. Operates on the mapping + data directly (not the output document), so it's a pure function with no filesystem dependency.
- Added `backend/app/api/routes/reports.py` (`POST /reports/generate`, `GET /reports/{id}/preview`, `GET /reports/{id}/download`) — same disposable-debug-route status as `/easr/lookup`/`/rera/lookup`. Preview reuses `DocumentParser.extract_docx_text()` (Phase 3) rather than new extraction logic. `report_id` is a server-generated UUID (validated by regex on the way back in) so preview/download never take a client-supplied filesystem path. Added `REPORTS_DIR` setting.
- Added `app/models/template_mapping.py` (`SkeletonLocation`, `FieldMapping`) — relocated out of `report_service.py` once `prompt_builder.py` and `claude_service.py` also needed it, to avoid a `report_service.py` → `claude_service.py` → `prompt_builder.py` → `report_service.py` import cycle.
- Added `backend/tests/test_report_service.py` additions (mapping cache, injection incl. a formatting-preservation assertion, quality check — 19 tests total in that file now), `backend/tests/test_claude_service.py` additions (mapping response parsing, tool-selection), and `backend/tests/test_reports_route.py` (4 tests, full generate → preview → download flow plus error cases). Full backend suite: 68/68 passing.
- Phase 6 (Report Generation) is now complete — all items checked off in `docs/ROADMAP.md`. Not yet exercised against a real Claude response (no API key yet) — the mapping call, retry behavior, and JSON-shape handling are only verified against fakes; first real template should be run through `/reports/generate` once the key is added.
