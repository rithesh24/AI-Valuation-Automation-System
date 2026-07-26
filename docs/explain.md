Good call — let's pause on commands and build your understanding instead. Let me first look at the files I haven't shown you yet, so the explanation is accurate rather than guessed.

  Read 15 files

Here's the backend, folder by folder, explained the way I'd walk a junior engineer through it on their first day.

The big picture first

FastAPI doesn't force a folder structure on you — this layout is a convention we chose, and it directly mirrors what docs/ARCHITECTURE.md mandates: one responsibility per module, keep things modular, avoid tight coupling. Every folder below exists to keep one kind of concern separate from the others, so that changing one thing (say, how we validate uploads) never requires touching something unrelated (say, how we log).

backend/
├── app/
│   ├── main.py          ← the entry point, wires everything together
│   ├── api/routes/       ← HTTP layer — "what URL does what"
│   ├── core/             ← cross-cutting setup (config, logging)
│   ├── models/           ← shared data shapes (currently empty, reserved)
│   └── services/         ← the actual business logic
├── tests/                ← automated tests, mirrors app/ structure
├── .venv/                ← isolated Python environment (not committed)
├── data/                 ← runtime output: uploaded files (not committed)
├── requirements.txt      ← production dependencies
├── requirements-dev.txt  ← dependencies only needed for testing
├── pytest.ini            ← tells pytest where to look for tests
└── .env / .env.example   ← secrets and config, read at startup

Now let's go through each one and why it's shaped that way.

---
app/main.py — the entry point

app = FastAPI(title="AVAS Backend", version="0.1.0")
app.add_middleware(CORSMiddleware, ...)
app.include_router(health_router)
app.include_router(uploads_router)

This is the only file that "assembles" the application. It doesn't contain any logic itself — it just creates the FastAPI app object, turns on CORS (explained below), and plugs in each route file. When you add a new feature area later (e.g. reports_router), this is the one line you add here — everything else about that feature lives elsewhere. That's the point: main.py stays small and boring forever.

Why CORS matters here specifically: your browser (localhost:3000) and your API server (localhost:8000) are technically different "origins" as far as a browser is concerned, even though they're both on your own machine. Browsers block cross-origin requests by default unless the server explicitly says "requests from this origin are allowed" — that's what CORSMiddleware + CORS_ORIGINS in your .env does. Without it, the upload screen you tested earlier would've failed silently with a CORS error in the browser console, even though curl worked fine (curl doesn't enforce CORS — only browsers do).

---
app/api/routes/ — the HTTP layer

This folder answers: "What URL, method, and shape does the outside world see?" Nothing more.

- health.py — GET /health, a trivial "is the server alive" check.
- uploads.py — POST /uploads, the endpoint your frontend calls.

Look at uploads.py again — it's deliberately thin:

@router.post("/uploads", response_model=list[UploadedFileInfo])
def upload_files(files, category, session_id):
    try:
        return upload_service.save_files(files, category, session_id)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

It doesn't know how validation works, how files get sanitized, or where they're stored. Its only jobs are: (1) parse the HTTP request into Python types, (2) call the service that actually does the work, (3) translate the service's own exception into an HTTP status code the browser understands. This split matters because it means upload_service.py can be tested directly in Python (like tests/test_uploads.py partly does) without spinning up a web server at all — and if we ever swap FastAPI for something else, only this thin layer would need to change.

__init__.py files inside api/ and api/routes/ are empty on purpose — their only job is telling Python "this folder is a package, you're allowed to import from it." No code needed inside.

---
app/core/ — cross-cutting setup

Things every part of the app needs, that don't belong to any one feature.

config.py:
class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

settings = Settings()
This uses pydantic-settings, a library that automatically reads your .env file and environment variables into a typed Python object. Two big wins over just using os.environ.get("FOO") scattered everywhere: (1) it's typed — MAX_UPLOAD_SIZE_MB is guaranteed to be an int, not a string you have to remember to convert; (2) it's one object (settings) imported wherever needed, so there's exactly one source of truth for configuration. This is also why API keys are safe: .env is git-ignored (see .gitignore), so ANTHROPIC_API_KEY never gets committed to source control — it only exists on your machine.

logging.py:
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="...")
One function, called once in main.py, that configures how every log line across the whole app gets formatted. Without this file, every module that wants to log something would need to configure logging itself — duplicated setup, easy to get inconsistent.

---
app/models/ — currently just a placeholder

Right now models/__init__.py is empty. This folder is reserved for Phase 5's "canonical data schema" (see docs/DECISIONS.md D9) — the Pydantic models that will describe what a fully-extracted valuation report looks like (owner name, survey number, area figures, etc.), shared between the extraction step, the template-mapping step, and the injection step. It exists now, empty, so the folder structure doesn't need to change later — but there's genuinely nothing to explain yet because nothing's been built here. We're intentionally not jumping ahead to Phase 5 (per CLAUDE.md's "Development Order" rule).

---
app/services/ — where the real work happens

This is the heart of the backend, and the one that maps 1:1 to the service list in docs/ARCHITECTURE.md. Each file is a class with one responsibility, and right now they're at very different stages:

┌────────────────────┬──────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────┐
│        File        │              Status              │                                    What it'll do                                     │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ upload_service.py  │ Implemented, tested              │ Validate + store uploaded files (Phase 2 — done)                                     │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ document_parser.py │ Stub (raise NotImplementedError) │ Extract text from PDFs/DOCX, OCR scanned docs (Phase 3)                              │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ easr_service.py    │ Stub                             │ Playwright automation against the Maharashtra eASR portal (Phase 4)                  │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ claude_service.py  │ Stub                             │ Talk to the Claude API — extraction, web-search research, template mapping (Phase 5) │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ prompt_builder.py  │ Stub                             │ Assemble the prompt text sent to Claude, no API calls itself (Phase 5)               │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ report_service.py  │ Stub                             │ The 3-stage pipeline that fills the Word template (Phase 6)                          │
├────────────────────┼──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ usage_service.py   │ Stub                             │ Track token counts and API cost (Phase 7)                                            │
└────────────────────┴──────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘

Why stubs instead of just not having the files yet? This was a Phase 1 decision — sketching every service's interface (method names, argument types, return types) up front, based directly on the responsibilities ARCHITECTURE.md already defined, so the overall shape of the system was visible from day one even though nothing was implemented. raise NotImplementedError is Python's honest way of saying "this method exists on paper, don't call it yet" — it'll fail loudly if something tries to use it prematurely, rather than silently doing nothing.

Notice none of these classes import each other. report_service.py doesn't import claude_service.py directly inside itself — coordination between services happens at a higher level (a route, eventually) that calls one service, then feeds its output into the next. That's what "avoid tight coupling" means in practice: each service can be unit-tested alone, swapped out, or rewritten without the others needing to know.

---
tests/ — automated verification

- test_health.py, test_uploads.py — one test file per thing being tested, using FastAPI's TestClient to simulate real HTTP requests without needing a running server.
- __init__.py — empty, same reason as elsewhere: makes tests importable as a package (some pytest configurations need this, some don't — it's here for consistency with the rest of app/).
- pytest.ini at the backend root just tells pytest: "look inside tests/ for test files" — so running plain pytest from backend/ finds everything automatically.

The reason test_uploads.py overrides upload_service with a temp directory (monkeypatch.setattr(...)) rather than writing real files into backend/data/ during tests is important: tests should never depend on or pollute real application state. Every test run gets a fresh, throwaway folder (pytest's tmp_path fixture), so tests stay fast and don't leave junk behind.

---
Dependency files — two, not one

- requirements.txt — what the application itself needs to run: fastapi, uvicorn (the server that actually runs FastAPI), pydantic-settings, python-multipart (needed specifically to parse file uploads).
- requirements-dev.txt — starts with -r requirements.txt (pull in everything above), then adds pytest and httpx (which TestClient needs under the hood). These are only needed by developers running tests, never by the shipped app — no reason to bloat the production install with them.

---
.venv/, data/, .pytest_cache/ — deliberately not committed to git

All three are in .gitignore. Each for a different reason:
- .venv/ — a virtual environment: an isolated copy of Python + installed packages, scoped just to this project. Without it, installing this project's dependencies would affect every Python project on your machine globally, and version conflicts between projects become a nightmare. It's regenerated by anyone from requirements.txt — no reason to commit gigabytes of installed packages.
- data/ — where uploaded files actually land at runtime (created the first time someone uploads something — that's why it didn't exist until we tested the upload flow). It's real user data, potentially containing sensitive property documents — it must never end up in git history.
- .pytest_cache/ — pytest's own bookkeeping (which tests passed last time, etc.), purely a local speed optimization, meaningless to anyone else.

---
Want me to walk through the frontend/ folder the same way next, or is backend enough for now?

✻ Worked for 1m 18s
                                                                                                           Update available! Run: winget upgrade Anthropic.ClaudeCode
───────────────────


next:
Here's a plain-language walkthrough of every file touched so far in this session, grouped by what they're for.

Backend code (the actual feature)

backend/app/services/document_parser.py — modified (was empty stubs, now has real code)
This is the class that knows how to pull text out of documents. Three public methods, matching what a valuer would upload:
- extract_pdf_text() — opens a PDF with a library called PyMuPDF, reads each page's text. If a page has almost no text (under 20 characters — meaning it's probably a scanned image, not real text), it automatically calls OCR on just that page instead.
- extract_docx_text() — opens a Word file with python-docx, walks through every paragraph and every table cell, and joins the text together.
- ocr_scanned_document() — for when a document is definitely an image with no text layer (a scanned page, or a photo of a document). It uses pytesseract, which is a Python wrapper around a separate program called Tesseract that "reads" text out of images.

There's also a small custom error class, DocumentParserError — instead of letting the app crash with a confusing Python error if a file is corrupt or a required program is missing, this wraps it in a clear message. This mirrors a pattern already used elsewhere in the codebase (UploadValidationError in upload_service.py).

backend/app/core/config.py — modified (added 2 lines)
This file holds app-wide settings (things that can be changed via a .env file without touching code). I added:
- TESSERACT_CMD — lets you tell the app exactly where the Tesseract program is installed, in case it's not automatically found.
- OCR_TRIGGER_CHAR_THRESHOLD — the "20 characters" cutoff mentioned above, as a configurable number instead of a hardcoded magic value buried in the code.

backend/requirements.txt — modified (4 new lines)
This is Python's shopping list of external libraries the project depends on. I added the four libraries the new code needs: PyMuPDF, python-docx, pytesseract, Pillow (an image-handling library pytesseract needs).

Tests

backend/tests/test_document_parser.py — new file
Automated tests that check the three methods above actually work, without needing you to manually create a PDF each time. It generates tiny throwaway PDF/DOCX/image files on the fly inside the test itself (using the same libraries), runs the extractor on them, and checks the output contains the expected text. If Tesseract isn't installed on whatever machine runs these tests, the OCR-specific tests politely skip instead of failing.

Project documentation (per this project's CLAUDE.md rules)

docs/ROADMAP.md — modified: checked off the 3 checkboxes under "Phase 3 - Document Processing".

docs/DECISIONS.md — modified: added entry "D13", a short paragraph recording why Tesseract was chosen over the alternative (EasyOCR) and what the 20-character threshold is, so future-you (or future-me) doesn't have to guess or re-debate it later.

docs/PROGRESS.md — modified: added a dated log entry summarizing what got built this session — this project's changelog, basically.

Not yet created

The backend/scripts/extract_text.py throwaway test script I described (a small command-line tool to run extraction on a real PDF you point it at) was not actually written — you interrupted that tool call before it saved, then switched to plan mode. Nothing on disk for that yet.
