from dataclasses import dataclass

from .books import Book, book_by_number
from .db import get_app_db, get_translation_db, get_state


@dataclass
class Verse:
    book: Book
    chapter: int
    verse: int
    text: str
    translation: str


def parse_verse_spec(spec: str) -> list[tuple[int, int]]:
    """Parse '1', '1-3', '1,5', '1-3,5,7-9' → list of (start, end) inclusive ranges."""
    ranges: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ranges.append((int(a), int(b)))
        else:
            n = int(part)
            ranges.append((n, n))
    return ranges


def fetch_verses(
    translation: str,
    book: Book,
    chapter: int,
    verse_spec: str | None = None,
) -> list[Verse]:
    conn = get_translation_db(translation)
    try:
        if verse_spec:
            rows = []
            for v_start, v_end in parse_verse_spec(verse_spec):
                rows.extend(conn.execute(
                    "SELECT verse, text FROM verses "
                    "WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse",
                    (book.number, chapter, v_start, v_end),
                ).fetchall())
        else:
            rows = conn.execute(
                "SELECT verse, text FROM verses WHERE book=? AND chapter=? ORDER BY verse",
                (book.number, chapter),
            ).fetchall()

        return [
            Verse(book=book, chapter=chapter, verse=r["verse"],
                  text=r["text"], translation=translation)
            for r in rows
        ]
    finally:
        conn.close()


def get_random_verse(translation: str, book: Book | None = None) -> Verse | None:
    conn = get_translation_db(translation)
    try:
        if book:
            row = conn.execute(
                "SELECT book, chapter, verse, text FROM verses WHERE book=? ORDER BY RANDOM() LIMIT 1",
                (book.number,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT book, chapter, verse, text FROM verses ORDER BY RANDOM() LIMIT 1",
            ).fetchone()

        if not row:
            return None
        b = book_by_number(row["book"])
        if not b:
            return None
        return Verse(book=b, chapter=row["chapter"], verse=row["verse"],
                     text=row["text"], translation=translation)
    finally:
        conn.close()


def get_chapter_count(translation: str, book: Book) -> int:
    conn = get_translation_db(translation)
    try:
        row = conn.execute(
            "SELECT MAX(chapter) AS mc FROM verses WHERE book=?", (book.number,)
        ).fetchone()
        return row["mc"] if row and row["mc"] else book.chapters
    finally:
        conn.close()


def get_default_translation() -> str:
    conn = get_app_db()
    try:
        return get_state(conn, "default_translation", "web")
    finally:
        conn.close()
