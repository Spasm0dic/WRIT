from .books import book_by_number
from .db import get_app_db


def add_bookmark(path: str, translation: str, book_num: int, chapter: int, verse: int) -> int:
    conn = get_app_db()
    try:
        cur = conn.execute(
            "INSERT INTO bookmarks (path, translation, book, chapter, verse) VALUES (?,?,?,?,?)",
            (path.strip("/"), translation, book_num, chapter, verse),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def list_bookmarks(path_prefix: str | None = None) -> list[dict]:
    conn = get_app_db()
    try:
        if path_prefix:
            rows = conn.execute(
                "SELECT * FROM bookmarks WHERE path LIKE ? ORDER BY path, created",
                (path_prefix.strip("/") + "%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bookmarks ORDER BY path, created"
            ).fetchall()

        result = []
        for r in rows:
            book = book_by_number(r["book"])
            result.append({
                "id":         r["id"],
                "path":       r["path"],
                "translation": r["translation"],
                "book":       r["book"],
                "book_name":  book.name if book else f"Book {r['book']}",
                "chapter":    r["chapter"],
                "verse":      r["verse"],
                "created":    r["created"],
            })
        return result
    finally:
        conn.close()


def get_bookmark(bookmark_id: int) -> dict | None:
    conn = get_app_db()
    try:
        row = conn.execute("SELECT * FROM bookmarks WHERE id=?", (bookmark_id,)).fetchone()
        if not row:
            return None
        book = book_by_number(row["book"])
        return {
            "id":         row["id"],
            "path":       row["path"],
            "translation": row["translation"],
            "book":       row["book"],
            "book_name":  book.name if book else f"Book {row['book']}",
            "chapter":    row["chapter"],
            "verse":      row["verse"],
        }
    finally:
        conn.close()


def remove_bookmark(bookmark_id: int) -> bool:
    conn = get_app_db()
    try:
        cur = conn.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
