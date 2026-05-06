import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.environ.get("VRS_DATA", Path.home() / ".local" / "share" / "vrs"))
TRANSLATIONS_DIR = DATA_DIR / "translations"
APP_DB_PATH = DATA_DIR / "vrs.db"

_APP_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL,
    translation TEXT    NOT NULL,
    book        INTEGER NOT NULL,
    chapter     INTEGER NOT NULL,
    verse       INTEGER NOT NULL,
    created     DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bm_path ON bookmarks(path);

CREATE TABLE IF NOT EXISTS notes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    book    INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse   INTEGER NOT NULL,
    text    TEXT    NOT NULL,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_bcv ON notes(book, chapter, verse);

CREATE TABLE IF NOT EXISTS reading_plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    day           INTEGER NOT NULL,
    book          INTEGER NOT NULL,
    chapter_start INTEGER NOT NULL,
    chapter_end   INTEGER NOT NULL,
    target_date   TEXT,
    done          INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_plan_name ON reading_plans(name, day);

CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    translation TEXT    NOT NULL,
    book        INTEGER NOT NULL,
    chapter     INTEGER NOT NULL,
    verse_start INTEGER,
    verse_end   INTEGER,
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS state (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)


def get_app_db() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(APP_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_APP_SCHEMA)
    conn.commit()
    return conn


def get_translation_db(translation: str) -> sqlite3.Connection:
    path = TRANSLATIONS_DIR / f"{translation.lower()}.db"
    if not path.exists():
        raise FileNotFoundError(
            f"Translation '{translation}' not found. "
            f"Run 'writ translations' to see what's installed, "
            f"or 'python scripts/import_translation.py' to add one."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def list_translations() -> list[str]:
    _ensure_dirs()
    return sorted(p.stem for p in TRANSLATIONS_DIR.glob("*.db"))


def get_state(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
