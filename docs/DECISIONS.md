# AVAS Architecture Decisions

Lightweight decision log. Each entry captures what was decided, and why — so decisions aren't relitigated later without new information.

---

## D1 — Single-user desktop application, no authentication (2026-07-22)
**Decision:** AVAS is a single-user local desktop tool. No login, accounts, or roles.
**Why:** Confirmed by the client; the valuer is the only operator of their own installation.
**Implication:** `usage_service.py` tracks usage globally per installation, not per-user.

## D2 — Maharashtra eASR is the only official-rates source for V1 (2026-07-22)
**Decision:** `easr_service.py` targets Maharashtra eASR exclusively in V1. Other states are out of scope until explicitly requested.

## D3 — Claude Sonnet is the AI model (2026-07-22)
**Decision:** `claude_service.py` uses Claude Sonnet for extraction, mapping, and report-content generation calls.

## D4 — Arbitrary bank templates, no predefined placeholders (2026-07-22)
**Decision:** The system must accept any bank's `.docx` template as uploaded, unmodified. No merge-field/placeholder tagging convention is required from the user.
**Why:** Banks supply their own templates as-is; requiring the valuer to pre-tag them defeats the purpose of automation.

## D5 — Three-stage template population pipeline (2026-07-22)
**Decision:** Report generation is split into three stages rather than asking Claude to generate a formatted document directly:
1. **Extraction** — Claude reads source documents + research data, returns structured data matching the canonical schema (see D9). No formatting involved.
2. **Mapping** — `report_service.py` parses the uploaded template with `python-docx`, extracts a structural skeleton (every paragraph/table/cell plus adjacent label text), and sends that skeleton to Claude (via `claude_service.py`) to map schema fields to skeleton locations.
3. **Injection** — code (not Claude) applies the mapping deterministically: existing `Run` objects have their `.text` replaced in place (inheriting existing formatting automatically); table rows are duplicated from an existing correctly-formatted row's XML rather than created fresh.
**Why:** LLMs are unreliable at reproducing exact visual formatting from a description, but reliable at semantic matching. Never generating new formatted elements — only cloning and mutating existing ones — guarantees fidelity (fonts, spacing, no shading, table margins) by construction instead of by hoping the model gets it right.
**Related:** D6 (mapping cache), D9 (schema).

## D6 — Template-mapping cache keyed by structural skeleton hash (2026-07-22)
**Decision:** The Stage-2 mapping result is cached, keyed by a hash of the *extracted skeleton* (not the raw file bytes). A manual "regenerate mapping" action is exposed in the UI, and cache entries (bank name, first-seen date) are visible to the valuer via the SQLite persistence layer.
**Why:** Valuers reuse the same handful of bank templates repeatedly — caching avoids re-running the mapping call (cost, latency, variance) for every report. Hashing raw file bytes was rejected because trivial re-saves (Word metadata changes) would cause unnecessary cache misses without any real layout change; hashing the skeleton instead means a genuinely-changed template (renamed label, moved section, new table column) always produces a new hash and triggers a fresh mapping, while a cosmetic re-save still hits the cache.

## D7 — No CAPTCHA on Maharashtra eASR — full Playwright automation in scope (2026-07-22)
**Decision:** Confirmed by the client that the Maharashtra eASR portal (igreval) does not present a CAPTCHA. `easr_service.py` can therefore perform fully unattended retrieval with retries, as originally scoped in `ARCHITECTURE.md`, without a human-in-the-loop step.

## D8 — Two-tier market/comparable research strategy (2026-07-22)
**Decision:**
- **Tier 1 (official/government data)** — Ready Reckoner/guideline value (via eASR), and potentially RERA/SRO if their public search pages prove similarly automatable — dedicated Playwright services, following the eASR pattern, returning structured data.
- **Tier 2 (comparable listings)** — 99acres, MagicBricks, Housing.com, and other heterogeneous public sources — handled via Anthropic's hosted web-search tool, attached to the Claude Messages API call in `claude_service.py`, rather than custom scrapers.
**Why:** Government portals are stable, structured, and safe to automate deterministically. Real-estate listing portals are numerous, change their DOM frequently, and scraping them carries ToS risk. Claude's own web-search tool already performs this kind of research (with citations, source URLs, and access dates) in the client's current manual workflow, so using it via the API preserves that behavior instead of rebuilding it as fragile scraper code.

## D9 — Canonical data schema derived from docs/PROMPTS.md (2026-07-22)
**Decision:** The Pydantic schema shared between services (extraction output, mapping input, injection input) will be based directly on the field list already present in the client's working prompt (`docs/PROMPTS.md`, Sections 4–11 and 24–26: property identification, ownership/title flow, area reconciliation, boundaries, site/building particulars, land use/statutory position, encumbrances, valuation calculation, concluded values), rather than designed from scratch.
**Why:** That prompt already encodes the client's real-world professional requirements (IVS/IBBI compliance) field-by-field; reinventing the schema risks missing something the client's current manual process already accounts for.

## D10 — SQLite as the local persistence layer (2026-07-22)
**Decision:** SQLite is added for usage tracking (tokens/cost/monthly stats), report generation history, and the template-mapping cache (D6).
**Why:** Desktop, single-user app; SQLite requires no separate server and is sufficient for this scale.

## D11 — Deterministic OCR fallback (2026-07-22)
**Decision:** OCR triggering will use an explicit rule (e.g., extracted text length below a threshold triggers OCR) rather than a vague "if required." Exact threshold to be set during Phase 3.

## D12 — Testing introduced progressively (2026-07-22)
**Decision:** Test coverage is added per phase as features are built, rather than deferred entirely to Phase 8. First instance: Phase 1 shipped with a passing pytest test against `/health`.

## D13 — Tesseract for OCR, 20-character-per-page trigger threshold (2026-07-24)
**Decision:** `document_parser.py` uses `pytesseract` (wrapping the Tesseract binary) for OCR, not EasyOCR. The Tesseract binary is an external dependency (not bundled by pip) — an optional `TESSERACT_CMD` setting lets it be pointed at a non-PATH install. The OCR trigger rule (D11) is: a PDF page whose extracted text layer is under 20 characters is treated as scanned and OCR'd instead. `ocr_scanned_document()` also accepts image files (.jpg/.jpeg/.png) directly, since `upload_service.py` allows property documents to be uploaded as photos of a scan, not just PDFs.
**Why:** Chosen over EasyOCR to keep the packaged Electron app's install size and first-run time down — EasyOCR pulls in PyTorch. Trade-off: end users need Tesseract installed (or the installer needs to bundle/install it) rather than it being a pure-Python dependency; that packaging step is deferred to Phase 9 (Production).

## D14 — eASR automation targets eASR 1.9 (dropdown-based), generic result schema, known V1 gaps (2026-07-24)
**Decision:** `easr_service.py` automates `https://easr.igrmaharashtra.gov.in/eASRCommon.aspx` (eASR 1.9, the classic dropdown-based portal) rather than `igreval.maharashtra.gov.in`'s "eASR 2.0 (Beta)", which turned out to be a map-click UI, not the dropdown flow the client's manual workflow actually used. Confirmed live: no CAPTCHA (D7 holds). District is selected via a `hDistName` URL query param (the on-page dropdown is disabled/display-only); Taluka and Village are real cascading dropdowns.

The result table's shape depends on the selected village, not the district: rural villages return an Assessment-Type/Range/Rate table; urban/municipal-corporation villages return the उपविभाग/Attribute grid matching the client's original Mumbai-based prompt, plus a "Search By: Survey No / Location" control. Because of this, `EASRGuidelineResult` uses a **generic schema** (`columns: list[str]` + `rows: list[dict[str, str | None]]`, scraped headers verbatim) instead of a fixed set of fields — a fixed schema would have been wrong for one of the two shapes.

Browser lifecycle: fresh Chromium browser/context/page per call, closed in `finally` — not shared/pooled (single-user desktop app, occasional per-property lookups, and it gives every retry a clean slate). Retries: 2 retries (3 attempts total), fixed backoff, only for Playwright `TimeoutError`/`Error`; `EASRServiceError` (bad input, missing Chromium, unrecognized district) fails immediately, no retry. No SQLite caching of lookup values (contrast with D6): eASR lookups are effectively unique per property, and a persisted cache has no clean invalidation trigger if the portal's published rate is later corrected — logging via the existing `logging` setup is enough for V1.

**Known V1 gaps (deliberately deferred, not silently missing):**
- Only a handful of `hDistName` identifiers are confirmed working ("Pune", "Thane", "Nagpur"); there's no full 36-district lookup table yet, and Mumbai City/Suburban's identifier was not found (they don't appear in their expected division's dropdown, suggesting a possibly different mechanism). Callers must supply the portal's exact identifier for now.
- Survey-number filtering on urban results only scans the first page of a village's subdivisions; villages with many subdivisions (multi-page results) may not surface a match beyond page 1. `EASRGuidelineResult.note` reports this explicitly when it happens, rather than silently returning an incomplete match as if it were final.
- A true "no data for this search" portal state was not observed/verified live; currently indistinguishable from a timeout, so it's treated as a retryable failure and eventually surfaces as `EASRServiceError` rather than `found=False`.
**Why:** These gaps were surfaced deliberately after driving the live portal end-to-end (not guessed), rather than either blocking Phase 4 entirely on solving them or silently shipping code that assumes they don't exist. Each is narrow, documented, and fixable independently when a real report-generation flow (Phase 5/6) needs it.

## D15 — RERA automation is feasible, SRO is not (2026-07-24)
**Decision:** Evaluated the Phase 4 stretch item (`official_sources_service.py`, per `docs/ARCHITECTURE.md`) live, the same way eASR was evaluated in D14:
- **MahaRERA project search** (`https://maharera.maharashtra.gov.in/projects-search-result` — note: `maharera.mahaonline.gov.in`, the commonly-cited URL, no longer resolves) has **no CAPTCHA**: a plain State/District/Project-Name/Registration-Number/Pincode form returning clean, paginated HTML (registration number, project name, promoter/developer name, district, certificate link). Same automatable shape as eASR. **Feasible** — built same day, see D16.
- **SRO / Index-II** (IGR Maharashtra's registered-document search) **requires a CAPTCHA** on every search, confirmed via multiple independent descriptions of the live flow. **Not feasible** for unattended automation under this project's constraints.
**Why:** RERA directly corroborates fields the client's document checklist already extracts manually ("RERA registration number", "RERA Certificate" — `docs/PROMPTS.md` field #29) with no CAPTCHA obstacle, so it's a genuine low-effort extension of the eASR pattern, not scope creep. SRO fails the same no-CAPTCHA precondition D7 required before eASR was judged automatable; solving it would mean either a CAPTCHA-solving service (the fragile/ToS-risky approach D8 already rejected for market-research scraping) or a human-in-the-loop step, which contradicts the fully-unattended design goal — so SRO is out of scope for V1, not deferred pending more research.
**Related:** D7, D8, D14.

## D16 — official_sources_service.py implements RERA project search (2026-07-24)
**Decision:** Built `official_sources_service.py` (`RERAService`) following D15's feasibility finding, mirroring `easr_service.py`'s conventions exactly: same per-call fresh-browser lifecycle, same retry contract (`RERAServiceError` for non-retryable failures — no search filter given, unrecognized district, missing Chromium — vs. retried Playwright timeouts/errors), same generic result philosophy. Search inputs: project name / MahaRERA registration number (one combined field, matching the portal's own field), district, pincode — at least one required. Result cards are parsed by adjacent-label text (`State`, `Pincode`, `District`, `Last Modified`, `Extension Certificate` each followed by their value on the next line) rather than fragile positional CSS selectors, since the portal's markup doesn't wrap label/value pairs in a clean structure. Added `POST /rera/lookup` as the same kind of disposable debug route as `/easr/lookup`.

**Known V1 gaps (same category as D14's, not silently missing):**
- Only the first results page (up to 10 projects) is scraped; broad searches (e.g. district-only) can match thousands of projects (`total_result_count` reports the true total so this is visible, not hidden) — fine for the intended use (looking up one specific project/registration number), not for browsing.
- A confirmed "zero results" state was observed live (empty result set, no crash) — this one is more solid than eASR's equivalent gap, since the result cards' *absence* is itself the found=False signal, with no dependency on recognizing a specific "no data" message.
**Why:** Same reasoning as D14 — ship the confirmed-working core path (single project/registration-number lookups, the realistic valuer use case) rather than block on full pagination support for a case (browsing thousands of projects) the report-generation flow won't actually need.
**Related:** D14, D15.

## D17 — Token tracking (usage_service.py) deferred (2026-07-25)
**Decision:** Implementation of `usage_service.py` (SQLite-backed token/cost tracking, per D10 — stdlib `sqlite3`, `record_usage()`/`get_monthly_usage()`, wired into `claude_service.py`'s successful extraction path, per-million-token pricing as configurable settings) was scoped and proposed but deferred at the client's request. `usage_service.py` remains a stub; Phase 5's "Token tracking" roadmap item stays unchecked.
**Why:** No dashboard exists yet to display usage (that's Phase 7) and no API key is set yet to generate real usage, so there's nothing to see even if it were built now — better to build it closer to when it's actually needed.
**Related:** D10.

## D18 — usage_service.py implemented; tracks both extraction and mapping calls (2026-07-26)
**Decision:** Implemented `UsageService` (D17's proposed design): stdlib `sqlite3`, a `usage_log` table (added to `app/core/db.py`'s shared schema alongside `template_mapping_cache`), `record_usage(input_tokens, output_tokens, stage)` and `get_monthly_usage(year, month)`. Wired into **both** of `claude_service.py`'s Claude call sites — Stage 1 extraction and Stage 2 mapping — not just extraction as D17's wording suggested. Cost is computed from two new settings, `ANTHROPIC_INPUT_PRICE_PER_MTOK` / `ANTHROPIC_OUTPUT_PRICE_PER_MTOK`, currently set to placeholder Sonnet-class list pricing ($3 / $15 per million tokens) pending real billing data.
**Why:** `ARCHITECTURE.md` assigns token/cost tracking to `claude_service.py` for all its Claude calls, not just extraction — mapping calls (Stage 2) cost real tokens too, and a dashboard that only counted extraction would understate actual spend. No live API key exists yet to source real pricing, so the per-token rates are an explicit placeholder rather than a guess presented as fact.
**Related:** D10, D17.

## D19 — Vitest + React Testing Library for frontend UI testing (2026-07-26)
**Decision:** Added `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`, and `@vitejs/plugin-react` as frontend devDependencies (`frontend/package.json`, `npm test`). Component/page-level tests only — no Playwright/Cypress browser E2E yet.
**Why:** Vitest needs no Babel config and has first-class TypeScript/ESM support, making it the lighter-weight option next to Jest for this small App Router codebase; Playwright would add browser binaries and a heavier setup for a value this project doesn't need yet (no real cross-page user flows to test beyond what component tests already cover). Excluded `vitest.config.ts` and `*.test.ts(x)` from `tsconfig.json`'s app-facing include list — `next build`'s type-check step otherwise fails on a duplicate nested `vite` package version pulled in transitively by `vitest`, which is irrelevant to the shipped app.
**Related:** none yet — revisit with Playwright if/when real multi-page browser flows need covering.

## D20 — POST /reports/generate-from-session: the missing pipeline orchestration (2026-07-26)
**Decision:** Added `ReportService.generate_full_report(session_id, ...)` and `UploadService.list_session_files(session_id, category)`, wired into a new `POST /reports/generate-from-session` route. Given only a `session_id`, it locates that session's uploaded template and property documents on disk, parses each document with `document_parser.py` (dispatched by extension), runs Stage 1 extraction via `claude_service.py`, then reuses the existing Stage 2/3 methods (`get_or_create_mapping`, `inject_data`, `run_quality_check`) unchanged. Added a matching frontend "Generate Report" section (`GenerateReportSection.tsx`) that appears on the home page once a template and at least one property document are uploaded, showing the quality-check result, an on-demand preview, and a download link.
**Why:** Every prior phase built and tested one stage of `ARCHITECTURE.md`'s Data Flow diagram (upload, parsing, extraction, mapping, injection) in isolation, but nothing actually chained them together outside of tests — `/reports/generate` (D5/D6) required the caller to already have a fully-formed `ValuationReportData`, which nothing in the app actually produced. This was a real gap between the app's checked-off roadmap items and what a user could click through, not a "nice to have." Tier 1 official-rate data (eASR) stays out of this endpoint for now — it needs the valuer to manually supply District/Taluka/Village/Survey No. (mirroring the client's real workflow, D14/D15), so it's left as `tier1_official_data: str | None`, populated by a future separate eASR step rather than built into this round.
**Related:** D5, D6, D14, D15.

## D21 — Phase 9 packaging: PyInstaller-bundled backend, Electron auto-launch + local static server, electron out of npm workspaces (2026-07-26)
**Decision:** Several linked decisions to make the packaged app self-contained:
1. **Backend bundling.** `backend/run_server.py` (a plain `uvicorn.run()` entrypoint — PyInstaller can't statically analyze the `uvicorn` CLI) + `backend/avas-backend.spec` (`collect_all` for `playwright` and `uvicorn`, whose implementations are chosen dynamically at runtime) produce a standalone `avas-backend.exe`. Port is read from `AVAS_BACKEND_PORT` (defaults to 8000) rather than hardcoded, so Electron controls it.
2. **Electron auto-launch.** `electron/src/main.ts` spawns `avas-backend.exe` (production only; dev still expects a manually-run `uvicorn`) and polls `/health` (20s timeout) before loading the UI, rather than assuming the backend is instantly ready.
3. **Local static server, not `loadFile`.** The frontend's static export is served over a real `http://127.0.0.1` origin (a small hand-rolled Node `http` server in `main.ts`, OS-assigned port) instead of `window.loadFile()`. Found by actually launching the packaged app: `loadFile()` resolves root-relative paths (every `<Link href="/dashboard">`) against the filesystem root (`file:///C:/dashboard`), not the app's own directory — not a corner case, it breaks every root-relative link in the shipped app. Serving over a real HTTP origin fixes the whole class of bug at once, the same way a real deployment would, rather than rewriting every `Link` to a relative path.
4. **`electron` removed from the root's npm `workspaces` array**, keeping its own independent `node_modules`. Found by actually running `electron-builder`: with `electron` hoisted into a shared workspace tree, electron-builder's internal "install production dependencies" step pruned packages it didn't recognize as belonging to `electron`'s own graph (`7zip-bin`, even the `tsc` shim) from the shared root `node_modules` — a known npm-workspaces/electron-builder interaction problem, not a config mistake on our end. `frontend` stays in the workspace; only `electron` needed isolating, since only it runs electron-builder's packaging step.
5. **NSIS installer generation is blocked in this dev environment specifically**, not by anything in the repo: electron-builder downloads macOS code-signing tooling (`winCodeSign`) for *any* Windows target (even unsigned, even `--dir`), and extracting it creates symlinks — which needs Windows Developer Mode enabled or an elevated terminal, neither available here. Verified everything short of that: the unpacked app (`electron/release/win-unpacked/AVAS.exe`) launches for real, spawns the bundled backend, health-checks it, serves the frontend via the local server, and `/dashboard` (the path that broke `loadFile()`) resolves correctly. Once Developer Mode or an elevated terminal is available, `npm run package` should complete the installer — the pipeline itself is confirmed correct.
**Why:** `PROJECT.md` calls for "commercial-grade software rather than a demonstration" — that means an end user who never sees Python, not one who runs `uvicorn` by hand. Playwright's Chromium download and the external Tesseract binary stay a documented manual one-time setup step (D13) rather than bundled — attempting to silently bundle a full browser binary and a system OCR engine into the installer was judged out of scope for this round.
**Related:** D5, D13.

## D22 — Removed a stray `docs` line from `.gitignore` (2026-07-26)
**Decision:** `.gitignore` had a bare `docs` entry that silently ignored any *new* file placed under `docs/` (pre-existing `docs/*.md` files were unaffected — they were already tracked before that line was added, and gitignore doesn't retroactively untrack files). Removed it.
**Why:** `CLAUDE.md` treats `docs/` as the project's source of truth — it should never be silently ignorable. Confirmed the bug by creating a throwaway probe file under `docs/` and running `git check-ignore -v` before removing the line.

## D23 — Bundle Chromium and Tesseract into the installer; skip code signing for now (2026-07-26)
**Decision:** Per client discussion, the two remaining manual-setup dependencies from D13/D21 are now bundled rather than left for the client to install:
- **`electron/scripts/prepareVendor.js`** (an electron-builder `beforeBuild` hook) stages Tesseract (from `C:\Program Files\Tesseract-OCR`, runtime files only — `tesseract.exe`, its `.dll`s, `tessdata`, not the training-tool executables/docs) and Playwright's Chromium (from `%LOCALAPPDATA%\ms-playwright\chromium-*`, copied whole) into `electron/vendor/` (gitignored — large binaries, never committed), which `extraResources` then copies into the packaged app as `resources/tesseract/` and `resources/playwright-browsers/`.
- **`backend/run_server.py`** now detects `sys.frozen` (true only for the actual PyInstaller exe, never in dev) and, if set, points `TESSERACT_CMD`/`PLAYWRIGHT_BROWSERS_PATH` at those bundled sibling folders (computed from `sys.executable`'s location) before `app.main` is imported — dev mode (`uvicorn --reload`) is completely unaffected and keeps using whatever's on the developer's own PATH/cache.
- Bundled rather than embedded in the PyInstaller `.exe` itself: PyInstaller's `--onefile` mode re-extracts its bundled data to a temp directory on *every* launch, which would mean re-extracting Chromium's ~330MB on every app start. Shipping them as plain `extraResources` (copied once, at install time) avoids that entirely.
- **Code signing skipped for this build.** The client will see a one-time Windows "Unknown Publisher" SmartScreen warning on first install/run. Acceptable for this handoff; revisit if/when a code-signing certificate is available.
**Why:** The client is a valuer, not a developer — asking them to run `playwright install chromium` and install Tesseract themselves isn't realistic for a commercial-grade deliverable (`PROJECT.md`'s stated goal). A code-signing certificate is a real cost/procurement decision, not something to default into without the client's input.
**Verified:** launched the bundled Tesseract binary against a rendered test image (`pytesseract.image_to_string`, correctly recognized the test text) and the bundled Chromium via `PLAYWRIGHT_BROWSERS_PATH` (launched, rendered a page, closed cleanly) — both using the exact staged paths the installer ships, not a proxy/approximation. Also re-verified the full packaged-app flow (backend auto-launch, health-check, local frontend server) still works with the larger resource set.
**Not yet done:** the NSIS installer step itself is still blocked on this dev machine's Developer Mode/elevated-terminal requirement (D21) — unrelated to this bundling work, same blocker as before. The unpacked app (`electron/release/win-unpacked/`) is now ~450MB larger (Chromium + Tesseract); the final installer will be similarly larger than a non-bundled build.
**Related:** D13, D21.
