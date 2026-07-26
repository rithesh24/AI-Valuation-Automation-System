# AI Valuation Automation System (AVAS)

Desktop application that automates preparation of professional property valuation reports for banks and financial institutions.

See `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` for full project scope, system design, and development phases.

## Project Structure

```
electron/           Electron desktop shell (TypeScript)
frontend/            Next.js frontend (TypeScript)
backend/              FastAPI backend (Python)
docs/                  Project documentation
templates/          Bank valuation templates (user-uploaded, not committed)
sample_documents/   Sample property documents for testing
```

## Setup

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

`playwright install chromium` is a one-time step separate from `pip install` — it downloads the actual browser binary that `easr_service.py` drives. Without it, eASR lookups fail with a clear "Chromium not installed" error rather than crashing.

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

This runs the frontend dev server and Electron together. Start the backend separately (see above).

## Testing

```
cd backend
pytest
```

```
cd frontend
npm test
```

## Packaging (Phase 9, D21, D23)

Produces a fully self-contained desktop build for the client: the FastAPI backend is bundled into a standalone `.exe` (PyInstaller) that Electron's main process spawns automatically and health-checks before showing the UI, and Chromium + Tesseract are bundled too — the client's machine needs to install nothing at all, not even the two setup steps below.

**On the *building* machine** (not the client's), before packaging:
```
playwright install chromium     # backend/ .venv active
```
Tesseract must already be installed at `C:\Program Files\Tesseract-OCR` (the standard installer location) — see https://github.com/UB-Mannheim/tesseract/wiki. `electron/scripts/prepareVendor.js` copies both into the package automatically; it fails loudly with a clear message if either is missing, rather than silently shipping a broken build.

```
pip install -r backend/requirements-dev.txt   # adds pyinstaller
npm install                                    # root + frontend workspace
cd electron && npm install                     # electron has its own independent node_modules — see D21
cd ..
npm run package
```

This builds the frontend static export, the backend `.exe` (`backend/dist/avas-backend.exe`), stages Chromium + Tesseract into `electron/vendor/`, and runs `electron-builder` (`electron/release/`). The unpacked app is ~450MB larger than a non-bundled build as a result — expected, not a bug.

**Known local-machine requirement:** producing the final NSIS installer needs either Windows **Developer Mode** enabled (Settings → Privacy & Security → For Developers) or an elevated (Administrator) terminal — electron-builder downloads code-signing tooling for any Windows target and extracting it creates symlinks, which needs that privilege. Without it, `npm run package` still produces a fully working unpacked app at `electron/release/win-unpacked/AVAS.exe` (verified working end-to-end, including the bundled Chromium/Tesseract); only the installer step is blocked.

**No code signing yet** (D23) — the client will see a one-time Windows "Unknown Publisher" warning on first install/run. Revisit if a code-signing certificate becomes available.
