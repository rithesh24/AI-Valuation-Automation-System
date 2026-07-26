"""PyInstaller entrypoint (Phase 9, D21). uvicorn's CLI can't be pointed at by
PyInstaller's static import analysis, so packaging needs a plain script that
calls uvicorn.run() directly. Also the process Electron's main.ts spawns in a
packaged build.
"""

import os
import sys
from pathlib import Path


def _configure_bundled_dependencies() -> None:
    """When running as the packaged PyInstaller exe (not `uvicorn --reload` in
    dev), Chromium and Tesseract are bundled alongside it as plain
    electron-builder extraResources — sibling folders under resources/ —
    rather than requiring the client's machine to install them (D23).

    Must run before `app.main` is imported: TESSERACT_CMD is read by
    document_parser.py at import time, and pydantic-settings reads
    environment variables when the Settings() singleton is constructed.
    """
    if not getattr(sys, "frozen", False):
        return

    resources_dir = Path(sys.executable).parent.parent  # resources/backend/ -> resources/

    browsers_dir = resources_dir / "playwright-browsers"
    if browsers_dir.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_dir)

    tesseract_exe = resources_dir / "tesseract" / "tesseract.exe"
    if tesseract_exe.is_file():
        os.environ["TESSERACT_CMD"] = str(tesseract_exe)


_configure_bundled_dependencies()

import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("AVAS_BACKEND_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
