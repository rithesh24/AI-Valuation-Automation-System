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
