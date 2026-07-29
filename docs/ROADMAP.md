# AVAS Development Roadmap

## Phase 1 - Project Foundation
- [x] Initialize Git
- [x] Setup Electron (scaffolded and verified: tsc build succeeds)
- [x] Setup Next.js (scaffolded and verified: next build succeeds)
- [x] Setup FastAPI (scaffolded and verified: pytest passes)
- [x] Configure project structure

---

## Phase 2 - File Upload System
- [x] Upload PDFs
- [x] Upload DOCX
- [x] Upload Images
- [x] File validation
- [x] Temporary storage

---

## Phase 3 - Document Processing
- [x] PDF text extraction
- [x] DOCX extraction
- [x] OCR integration

---

## Phase 4 - Browser Automation
- [x] Playwright setup
- [x] eASR automation (confirmed: no CAPTCHA, fully unattended)
- [x] Retry mechanism
- [x] Error handling
- [x] Evaluate RERA/SRO automation feasibility (stretch, per-source) — RERA feasible (no CAPTCHA), SRO not feasible (CAPTCHA-gated); see D15.
- [x] `official_sources_service.py` (RERA project search) — implemented and verified live; see D16.

---

## Phase 5 - AI Integration
- [x] Canonical data schema (derived from docs/UPDATED_PROMPTS.md Stage 1, sections 2-20)
- [x] Prompt Builder
- [x] Claude API (Stage 1 extraction call — retries, JSON parsing; no API key set yet, see PROGRESS.md)
- [x] Web-search tool integration for Tier 2 comparable research (99acres, MagicBricks, etc.) — tool attached, not yet verified live
- [x] Token tracking

---

## Phase 6 - Report Generation
- [x] Template skeleton extraction (python-docx)
- [x] Claude-assisted field-to-template mapping
- [x] Mapping cache (keyed by template skeleton hash) + manual regenerate override
- [x] Clone-and-fill DOCX injection (preserve formatting)
- [x] Automated final quality-check validation pass
- [x] Preview report
- [x] Download DOCX
- [x] PDF bank-template support (client feedback, 2026-07-29) — converts to .docx once, reuses the existing pipeline unchanged

---

## Phase 7 - Dashboard
- [x] Token usage
- [x] API cost
- [x] Monthly statistics

---

## Phase 8 - Testing
- [x] Unit tests
- [x] Integration tests
- [x] UI testing
- [ ] Live end-to-end test against the real Claude API — key is now configured and the pipeline was run live; fixed a real max_tokens/adaptive-thinking bug in the process (see D27), but hit a second, different, still-unresolved error ("Claude response did not match the expected schema: Expecting value...") — not yet passing end-to-end

---

## Phase 9 - Production
- [x] Build Electron app (auto-launches the bundled backend, serves the frontend locally — see D21)
- [ ] Package installer (Chromium + Tesseract now bundled, client needs to install nothing — D23; NSIS build itself still blocked on Developer Mode/elevated terminal for this dev machine — pipeline verified correct via the unpacked build, see D21)
- [x] Client-facing Settings screen for the Anthropic API key, no .env editing required (2026-07-29) — see D26
- [x] Documentation (README packaging section)