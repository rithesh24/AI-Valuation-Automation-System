# AVAS — AI Valuation Automation System

A desktop application that automates the preparation of professional property valuation reports for banks and financial institutions — built for a licensed property valuer, not a developer.

A valuer uploads a property's supporting documents and their bank's own valuation report template (any bank's format, as-is — no pre-tagging required). The system extracts and reconciles the property's details, pulls the official government guideline rate automatically, researches live comparable market evidence, and fills the exact uploaded template — preserving its formatting byte-for-byte — into a ready-to-review Word document.

Unlike a generic "AI writes your document" tool, AVAS never lets the AI touch formatting directly. It is designed around one hard rule: **the AI decides *what* the report says; deterministic code decides *how* it's laid out.**

---

## Core Idea

The valuer provides:
- Property-related documents (agreements, title deeds, approved plans, permissions, tax bills, photographs, etc. — PDF, DOCX, or scanned images)
- The bank's own valuation report template (`.docx` or `.pdf`), used exactly as uploaded
- Optional supporting images

AVAS runs that input through a pipeline that:
- Extracts and reconciles every relevant fact from the documents
- Retrieves the official government guideline rate for the property automatically, with no manual lookup
- Researches current comparable transactions from public sources, each one traceable to a real source and date
- Matches the extracted facts to the correct location in the bank's own template
- Writes the final report by editing the template's existing formatted elements in place — never generating new formatting from scratch

The output is a complete, professionally formatted Word document, ready for the valuer's review before submission.

---

## Key Capabilities

### Arbitrary Bank Templates, No Pre-Tagging

Any bank's `.docx` template is accepted exactly as uploaded — no merge fields, no placeholder conventions, no manual setup. A `.pdf` template (born-digital) is supported too, converted to `.docx` once and cached, so every downstream stage stays unaware it ever started as a PDF.

### Three-Stage Report Generation Pipeline

Report generation is deliberately never a single "AI, write me a document" call. It's split into three stages so that formatting fidelity is guaranteed by construction, not by hoping the model gets it right:

1. **Extraction** — Claude reads the parsed documents and produces structured data matching a 350+ field canonical schema (ownership, title flow, area reconciliation, boundaries, statutory position, valuation calculations, and more). No formatting involved at all at this stage.
2. **Mapping** — the uploaded template's structure (every paragraph and table cell, plus its nearby label text) is extracted with `python-docx` and sent to Claude once per *unique template shape* — not once per report. The result is cached, keyed by a hash of the template's structure alone (not its filled-in data or raw bytes), so re-uploading the same bank's format never re-triggers the mapping call.
3. **Injection** — plain code applies the mapping deterministically: existing `Run` objects have their text mutated in place (inheriting formatting automatically), and repeating table rows are cloned from an existing correctly-formatted row's XML. Nothing is ever built from scratch.

### Non-Fabrication by Design

Every fact in the output must trace back to an uploaded document, a government record, a disclosed public source, or a clearly flagged professional assumption. Where information genuinely isn't available, the field is retained and marked unavailable — never guessed, never silently dropped. This is enforced at the schema level: every field defaults to an explicit "unavailable" sentinel, so missing data is represented the same way as real data, with no special-case null handling anywhere downstream.

### Automated Official Government Rate Lookup

The Maharashtra eASR (Ready Reckoner / guideline value) portal is automated end-to-end with Playwright — no CAPTCHA, fully unattended. District/Taluka/Village/Survey Number extracted during Stage 1 automatically drive this lookup with no manual entry required, with fuzzy matching against the portal's real dropdown options and a legacy-portal fallback for known data gaps. A manual override form remains available if auto-lookup can't confidently resolve a match.

### RERA Project Verification

MahaRERA's project search is automated the same way, to verify registration details, promoter information, and project status where applicable.

### Two-Tier Market Research

- **Tier 1 (official/government data)** — dedicated Playwright automation (eASR, RERA), returning structured, statutory-grade data.
- **Tier 2 (comparable listings)** — Claude's own hosted web-search tool, attached directly to the extraction call, rather than custom scrapers against real-estate portals. Every comparable is recorded with its source, date, and URL.

### Automated Quality Check

Before handoff to preview, the system flags any field holding real (non-"unavailable") data that failed to land anywhere in the final document — distinct from fields honestly disclosed as unavailable, which are not treated as failures.

### Usage Dashboard

Token counts (exact, straight from the API) and estimated cost (based on configured per-token pricing) are tracked per request and aggregated monthly, backed by a local SQLite database.

### Client-Owned API Key

A Settings screen inside the app lets the valuer paste in their own Anthropic API key directly — no `.env` file editing, no restart required.

### Fully Self-Contained Desktop Packaging

The Electron shell auto-launches the bundled backend and health-checks it before showing the UI. Chromium (for the Playwright automation) and Tesseract (for OCR) are both bundled into the installer — the client's machine needs to install nothing at all.

---

## Pipeline Architecture

```
Upload           Property documents, bank template (.docx/.pdf), optional images
                 Saved to a session-scoped folder, validated by type and size

Parsing          PDF text extraction (PyMuPDF), DOCX extraction (python-docx)
                 OCR fallback for scanned pages, triggered automatically per page

Official Data    Maharashtra eASR guideline-rate lookup (Playwright), auto-chained
                 from the District/Taluka/Village/Survey No. extracted below
                 RERA project verification, where applicable

Extraction       Claude reads the parsed documents + official data
 (Stage 1)       -> structured data matching the canonical valuation schema
                 Claude's hosted web-search tool researches live comparables
                 (Tier 2), each grounded with a source, date, and URL

Mapping          The template's structure (paragraphs, table cells, nearby
 (Stage 2)       label text) is extracted and sent to Claude once per unique
                 template shape -- cached by a hash of the structure itself,
                 not the filled-in data, so the same bank format is never
                 re-mapped on a later report

Injection        Deterministic python-docx: existing Run objects have their
 (Stage 3)       text mutated in place (inherits formatting automatically);
                 table rows are cloned from an existing formatted row's XML.
                 Code never invents new formatting -- only clones and fills.

Quality Check    Flags any real (non-"unavailable") field with no mapped
                 location, before handoff to preview

Preview/Download The valuer reviews the generated .docx and downloads it
```

Every stage fails independently — if Playwright can't reach a government portal, or a data point simply isn't found, the pipeline continues and the affected fields are marked unavailable rather than the whole report failing.

---

## Technology Stack

### Desktop
- Electron

### Frontend
- Next.js 14 (App Router)
- React
- TypeScript
- Plain CSS design system (no UI framework dependency)

### Backend
- Python
- FastAPI

### AI
- Anthropic Claude (Sonnet 5) — document extraction, template-field mapping, and (via its hosted web-search tool) live comparable market research

### Browser Automation
- Playwright (Chromium) — Maharashtra eASR guideline-rate lookup, MahaRERA project search

### Document Processing
- PyMuPDF — PDF text extraction
- python-docx — reading and writing `.docx` templates and reports
- pdf2docx — one-time PDF-template-to-DOCX conversion
- pytesseract / Tesseract — OCR for scanned documents

### Persistence
- SQLite (stdlib `sqlite3`, no ORM) — usage/cost history, template-mapping cache

### Testing
- pytest (backend)
- Vitest + React Testing Library (frontend)

### Packaging
- PyInstaller (backend, onedir build)
- electron-builder (NSIS installer, Windows)

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key with funded credit ([console.anthropic.com](https://console.anthropic.com))

### Backend (FastAPI)

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium
copy .env.example .env
uvicorn app.main:app --reload
```

`playwright install chromium` is a one-time step separate from `pip install` — it downloads the actual browser binary the eASR/RERA automation drives. Without it, those lookups fail with a clear "Chromium not installed" error rather than crashing.

### Frontend (Next.js)

```
cd frontend
npm install
npm run dev
```

### Electron

```
cd electron
npm install
npm run dev
```

### Everything from the root

```
npm install
npm run dev
```

Runs the frontend dev server and Electron together. Start the backend separately (see above).

### Open

http://localhost:3000

---

## Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_PATH=data/avas.db
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-5
ANTHROPIC_MAX_RETRIES=2
ANTHROPIC_RETRY_DELAY_SECONDS=3.0
ANTHROPIC_INPUT_PRICE_PER_MTOK=3.0
ANTHROPIC_OUTPUT_PRICE_PER_MTOK=15.0
CORS_ORIGINS=http://localhost:3000
ENV=development
UPLOAD_DIR=data/uploads
MAX_UPLOAD_SIZE_MB=25
REPORTS_DIR=data/reports
TESSERACT_CMD=
OCR_TRIGGER_CHAR_THRESHOLD=20
EASR_HEADLESS=True
EASR_TIMEOUT_MS=30000
EASR_MAX_RETRIES=2
EASR_RETRY_DELAY_SECONDS=3.0
EASR_MAX_RESULT_PAGES=10
```

The API key can also be set from inside the app itself (Settings screen) instead of editing this file directly — the intended path for the client-facing build.

### Frontend

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## API Reference

### Base URL

`http://localhost:8000`

### Endpoints

```
POST  /uploads                          Upload property documents, template, or images
POST  /easr/lookup                      Manual Maharashtra eASR guideline-rate lookup
POST  /rera/lookup                      Manual MahaRERA project search
POST  /reports/generate                 Generate a report from already-extracted data
POST  /reports/generate-from-session    Full pipeline: parse -> extract -> map -> inject
GET   /reports/progress/{session_id}    Live generation progress
GET   /reports/{report_id}/preview      Preview the generated report's text
GET   /reports/{report_id}/download     Download the generated .docx
GET   /usage/monthly                    Token usage and estimated cost for a month
GET   /settings/api-key                 Whether an API key is currently configured
PUT   /settings/api-key                 Set the Anthropic API key from the app itself
GET   /health                           Backend liveness check
```

---

## Key Engineering Concepts

- **AI decides content, code decides formatting** — the three-stage pipeline exists specifically so Claude is never asked to reproduce exact visual formatting; that responsibility belongs entirely to deterministic code cloning existing document elements.
- **Structural, not content-based, caching** — the template-mapping cache is keyed by a hash of the template's *structure*, so two different filled reports from the same bank format still hit the cache, while an actually-changed template (a renamed label, an added column) correctly misses it.
- **Non-fabrication enforced at the schema level** — an explicit "unavailable" sentinel default means missing data is representable the same way as real data everywhere downstream, with no null-handling special cases.
- **Independent service failure** — Playwright, OCR, or a research step failing never crashes report generation; the affected fields are simply marked unavailable and the pipeline continues.
- **Onedir over onefile packaging** — the bundled Python backend ships as a plain folder rather than a self-extracting single executable, so it doesn't re-extract itself (and get re-scanned by antivirus software) on every single launch.
- **Loopback-only CORS** — scoped deliberately to a single-user local desktop app talking only to itself, not a hosted multi-tenant API.

---

## Positioning

**A production-oriented alternative to manually assembling bank property valuation reports** — combining AI-driven document understanding, real government-data automation, and byte-level template fidelity, wrapped in a fully self-contained desktop app built for a licensed valuer, not a developer.

---

## Future Improvements

- Live end-to-end validation of extraction and mapping quality against a funded API key, on real client reports
- Code-signed installer (removes the one-time "Unknown Publisher" Windows warning)
- Broader Maharashtra eASR district coverage beyond the currently-seeded set
- Guideline-rate automation for states beyond Maharashtra
- SRO/Index-II document search automation (currently blocked by a CAPTCHA on every search)
