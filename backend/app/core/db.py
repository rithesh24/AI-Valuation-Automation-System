"""Minimal SQLite persistence layer (D10) — single-user desktop app, no
server needed. Each caller owns its own table(s); this module only owns
connection lifecycle (schema creation, commit, close).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS template_mapping_cache (
    skeleton_hash TEXT PRIMARY KEY,
    bank_name TEXT NOT NULL DEFAULT '',
    first_seen_at TEXT NOT NULL,
    mapping_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    stage TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL
);
"""


@contextmanager
def get_connection():
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
