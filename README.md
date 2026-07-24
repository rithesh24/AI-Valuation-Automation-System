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
