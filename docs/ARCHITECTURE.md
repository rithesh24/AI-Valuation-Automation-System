# AI Valuation Automation System (AVAS)

# System Architecture

## Overview

AVAS follows a modular desktop application architecture.

The application consists of four primary layers:

1. Electron Desktop Application
2. Next.js Frontend
3. FastAPI Backend
4. External Services

Each layer has a single responsibility and communicates through well-defined interfaces.

---

# High-Level Architecture

┌─────────────────────────────┐
│       Electron Desktop      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Next.js Frontend       │
└──────────────┬──────────────┘
               │ REST API
               ▼
┌─────────────────────────────┐
│       FastAPI Backend       │
└──────────────┬──────────────┘
               │
 ┌─────────────┼─────────────────────────────┐
 ▼             ▼             ▼              ▼
Claude API   Playwright   Document Parser   DOCX Generator

---

# Application Layers

## Electron

Responsibilities

- Desktop shell
- Native window management
- File dialogs
- Local filesystem access
- Application packaging

Electron should NOT contain business logic.

---

## Frontend (Next.js)

Responsibilities

- User Interface
- Upload screens
- Dashboard
- Report preview
- API communication
- Progress indicators
- Error notifications

Frontend must never perform AI processing.

---

## Backend (FastAPI)

Responsibilities

- Business logic
- Document processing
- AI orchestration
- Browser automation
- Report generation
- Validation
- Logging

All application logic resides here.

---

# Backend Services

Each service should have one responsibility.

## upload_service.py

Responsibilities

- Validate uploaded files
- Save temporary files
- Organize uploads

---

## document_parser.py

Responsibilities

- Extract text from PDFs
- Read DOCX files
- OCR scanned documents

---

## easr_service.py

Responsibilities

- Launch Playwright
- Retrieve Maharashtra eASR data (V1 scope; no other states)
- Handle retries
- Return structured data

Confirmed: the Maharashtra eASR portal (igreval) presents no CAPTCHA, so retrieval can be fully unattended (no human-in-the-loop step required).

If retrieval fails:

Return error

Do not crash application.

---

## official_sources_service.py (Tier 1 research, stretch goal)

Responsibilities

- Follow the same Playwright pattern as `easr_service.py` for other official/government data sources (e.g. RERA, SRO) where their public search pages prove similarly automatable.
- Return structured data.

This is a stretch item, evaluated per-source as each is investigated — not guaranteed for every source.

---

## prompt_builder.py

Responsibilities

- Combine extracted information
- Combine eASR results
- Build Claude prompt

No API calls here.

---

## claude_service.py

Responsibilities

- Send prompts
- Receive responses
- Handle retries
- Track tokens
- Track API cost
- Perform Tier 2 comparable/market research (99acres, MagicBricks, Housing.com, etc.) via Anthropic's hosted web-search tool attached to the Messages API call, rather than custom scrapers
- Perform the template field-to-skeleton mapping call (Stage 2 of report generation — see `report_service.py`)

Only this service communicates with Claude.

---

## report_service.py

Report generation is a three-stage pipeline. Claude never generates document formatting directly — it only generates content; code owns fidelity by cloning and mutating existing formatted elements rather than creating new ones.

Responsibilities

1. **Extraction** — combine document-parser output and research data into structured data matching the canonical schema (no formatting involved). Performed via `claude_service.py`.
2. **Mapping** — parse the uploaded `.docx` template with `python-docx`, extract a structural skeleton (every paragraph/table/cell plus adjacent label text), and request a field-to-location mapping from Claude via `claude_service.py`. Cache the mapping, keyed by a hash of the extracted skeleton (not the raw file bytes), in the SQLite persistence layer. Expose a manual "regenerate mapping" override.
3. **Injection** — apply the mapping deterministically: edit the `.text` of existing `Run` objects in place (inherits existing formatting automatically); duplicate an existing correctly-formatted table row's XML for new rows rather than creating one from scratch.
4. Run an automated final quality-check validation pass (no placeholder/empty fields left behind) before handing off to preview.

---

## Persistence (SQLite)

Responsibilities

- Token/cost/usage history
- Report generation history
- Template structural-mapping cache (keyed by skeleton hash — see `report_service.py`)

Desktop, single-user scale — no separate database server required.

---

## usage_service.py

Responsibilities

- Token tracking
- Cost estimation
- Monthly usage
- Budget limits

---

# Data Flow

User uploads documents

↓

Validation

↓

Document Parsing

↓

Official Data Research (Playwright — eASR, and other official sources where feasible)

↓

Prompt Builder

↓

Claude API — Extraction + Tier 2 comparable research (web-search tool)

↓

Template Mapping (Claude-assisted, cached by template skeleton hash)

↓

DOCX Generator (clone-and-fill injection)

↓

Preview

↓

Download

---

# Error Handling

Every service must fail independently.

Example:

Playwright fails

↓

Continue report generation

↓

Notify user

↓

Fields become

"Information Not Available"

The application must never terminate because one service fails.

---

# AI Design Principles

Claude should:

- Never hallucinate
- Never invent values
- Never estimate property information
- Never overwrite verified information

If data is missing:

Return

Information Not Available

---

# Security

- API keys stored in .env
- Never expose API keys to frontend
- Validate every uploaded file
- Limit upload size
- Sanitize file names

---



# Development Principles

- Keep modules independent.
- Keep services small.
- One responsibility per service.
- Avoid tight coupling.
- Prefer composition over large classes.
- Write readable code before clever code.
- Production quality over speed.

---

# Guiding Principle

Every feature should be implemented as an independent module that can be modified, tested, or replaced without affecting the rest of the application.