import re
from datetime import date
from pathlib import Path

from .books import resolve_book, book_by_number
from .db import get_app_db, get_state, set_state


# ── Plan file parsing ─────────────────────────────────────────────────────────

def _parse_line(line: str) -> dict | None:
    """
    Accepts two formats:
      YYYY-MM-DD  book  chapter[-chapter]
      book  chapter[-chapter]
    Returns dict or None for blank/comment lines.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.+)$", line)
    if date_match:
        target_date = date_match.group(1)
        rest = date_match.group(2).strip()
    else:
        target_date = None
        rest = line

    parts = rest.split()
    if len(parts) < 2:
        return None

    book = resolve_book(parts[0])
    if not book:
        return None

    chapter_spec = parts[1]
    if "-" in chapter_spec:
        c_start, c_end = chapter_spec.split("-", 1)
        chapter_start, chapter_end = int(c_start), int(c_end)
    else:
        chapter_start = chapter_end = int(chapter_spec)

    return {
        "book":          book.number,
        "chapter_start": chapter_start,
        "chapter_end":   chapter_end,
        "target_date":   target_date,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

def load_plan(name: str, filepath: Path) -> int:
    """Import a plan file, replacing any existing plan with the same name."""
    conn = get_app_db()
    try:
        conn.execute("DELETE FROM reading_plans WHERE name=?", (name,))

        entries = []
        day = 1
        with open(filepath, encoding="utf-8") as fh:
            for line in fh:
                entry = _parse_line(line)
                if entry:
                    entries.append((
                        name, day,
                        entry["book"], entry["chapter_start"], entry["chapter_end"],
                        entry["target_date"],
                    ))
                    day += 1

        conn.executemany(
            "INSERT INTO reading_plans (name, day, book, chapter_start, chapter_end, target_date) "
            "VALUES (?,?,?,?,?,?)",
            entries,
        )
        conn.commit()
        return len(entries)
    finally:
        conn.close()


def list_plans() -> list[str]:
    conn = get_app_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT name FROM reading_plans ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def get_active_plan() -> str | None:
    conn = get_app_db()
    try:
        val = get_state(conn, "active_plan", "")
        return val or None
    finally:
        conn.close()


def set_active_plan(name: str) -> None:
    conn = get_app_db()
    try:
        set_state(conn, "active_plan", name)
    finally:
        conn.close()


def get_plan_progress(name: str) -> dict:
    conn = get_app_db()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM reading_plans WHERE name=?", (name,)
        ).fetchone()["c"]
        done = conn.execute(
            "SELECT COUNT(*) AS c FROM reading_plans WHERE name=? AND done=1", (name,)
        ).fetchone()["c"]
        return {"total": total, "done": done, "remaining": total - done}
    finally:
        conn.close()


def get_next_entry(plan_name: str) -> dict | None:
    conn = get_app_db()
    try:
        row = conn.execute(
            "SELECT * FROM reading_plans WHERE name=? AND done=0 ORDER BY day LIMIT 1",
            (plan_name,),
        ).fetchone()
        if not row:
            return None
        return _row_to_entry(row)
    finally:
        conn.close()


def mark_entry_done(entry_id: int) -> None:
    conn = get_app_db()
    try:
        conn.execute("UPDATE reading_plans SET done=1 WHERE id=?", (entry_id,))
        conn.commit()
    finally:
        conn.close()


# ── Catch-up logic ────────────────────────────────────────────────────────────

def days_behind(plan_name: str) -> int:
    """Return how many undone entries have a target_date in the past."""
    conn = get_app_db()
    try:
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM reading_plans "
            "WHERE name=? AND done=0 AND target_date IS NOT NULL AND target_date < ?",
            (plan_name, today),
        ).fetchone()
        return row["c"]
    finally:
        conn.close()


def get_catchup_entries(plan_name: str) -> list[dict]:
    """All undone entries with target_date <= today."""
    conn = get_app_db()
    try:
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM reading_plans "
            "WHERE name=? AND done=0 AND target_date IS NOT NULL AND target_date <= ? "
            "ORDER BY day",
            (plan_name, today),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]
    finally:
        conn.close()


def reset_plan_to_today(plan_name: str) -> None:
    """Mark all past entries as done; today's entry becomes the next."""
    conn = get_app_db()
    try:
        today = date.today().isoformat()
        conn.execute(
            "UPDATE reading_plans SET done=1 WHERE name=? AND target_date < ?",
            (plan_name, today),
        )
        conn.commit()
    finally:
        conn.close()


# ── Helper ────────────────────────────────────────────────────────────────────

def _row_to_entry(row) -> dict:
    book = book_by_number(row["book"])
    return {
        "id":            row["id"],
        "day":           row["day"],
        "book":          row["book"],
        "book_name":     book.name if book else f"Book {row['book']}",
        "chapter_start": row["chapter_start"],
        "chapter_end":   row["chapter_end"],
        "target_date":   row["target_date"],
    }
