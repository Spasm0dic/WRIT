from .books import book_by_number
from .db import get_app_db


def upsert_note(book_num: int, chapter: int, verse: int, text: str) -> None:
    conn = get_app_db()
    try:
        conn.execute(
            """INSERT INTO notes (book, chapter, verse, text)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(book, chapter, verse)
               DO UPDATE SET text=excluded.text, updated=CURRENT_TIMESTAMP""",
            (book_num, chapter, verse, text),
        )
        conn.commit()
    finally:
        conn.close()


def get_note(book_num: int, chapter: int, verse: int) -> str | None:
    conn = get_app_db()
    try:
        row = conn.execute(
            "SELECT text FROM notes WHERE book=? AND chapter=? AND verse=?",
            (book_num, chapter, verse),
        ).fetchone()
        return row["text"] if row else None
    finally:
        conn.close()


def get_notes_for_chapter(book_num: int, chapter: int) -> dict[int, str]:
    """Return {verse_num: note_text} for all noted verses in a chapter."""
    conn = get_app_db()
    try:
        rows = conn.execute(
            "SELECT verse, text FROM notes WHERE book=? AND chapter=? ORDER BY verse",
            (book_num, chapter),
        ).fetchall()
        return {r["verse"]: r["text"] for r in rows}
    finally:
        conn.close()


def list_notes(book_num: int | None = None, chapter: int | None = None) -> list[dict]:
    conn = get_app_db()
    try:
        if book_num and chapter:
            rows = conn.execute(
                "SELECT * FROM notes WHERE book=? AND chapter=? ORDER BY verse",
                (book_num, chapter),
            ).fetchall()
        elif book_num:
            rows = conn.execute(
                "SELECT * FROM notes WHERE book=? ORDER BY chapter, verse",
                (book_num,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY book, chapter, verse"
            ).fetchall()

        result = []
        for r in rows:
            book = book_by_number(r["book"])
            result.append({
                "book_name": book.name if book else f"Book {r['book']}",
                "chapter":   r["chapter"],
                "verse":     r["verse"],
                "text":      r["text"],
                "updated":   r["updated"],
            })
        return result
    finally:
        conn.close()


def remove_note(book_num: int, chapter: int, verse: int) -> bool:
    conn = get_app_db()
    try:
        cur = conn.execute(
            "DELETE FROM notes WHERE book=? AND chapter=? AND verse=?",
            (book_num, chapter, verse),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
