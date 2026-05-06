#!/usr/bin/env python3
"""
Import a Bible translation into writ's SQLite format.

Supported input formats:
  --format csv      b,c,v,t  (book-number, chapter, verse, text)
                    Header row optional; b can be integer or USFM book code.
  --format tsv      book<TAB>chapter<TAB>verse<TAB>text
                    book can be integer, USFM code, or full name.
  --format vpl      Verse-per-line: "GEN 1:1 In the beginning..."

Output: ~/.local/share/writ/translations/<name>.db

Usage examples:
  python scripts/import_translation.py web.csv -n web --format csv
  python scripts/import_translation.py kjv.tsv -n kjv --format tsv
  python scripts/import_translation.py kjv.txt -n kjv --format vpl
"""
import argparse
import csv
import os
import re
import sqlite3
import sys
from pathlib import Path

# ── USFM 3-letter code → book number ─────────────────────────────────────────
USFM_TO_NUM: dict[str, int] = {
    "GEN": 1,  "EXO": 2,  "LEV": 3,  "NUM": 4,  "DEU": 5,
    "JOS": 6,  "JDG": 7,  "RUT": 8,  "1SA": 9,  "2SA": 10,
    "1KI": 11, "2KI": 12, "1CH": 13, "2CH": 14, "EZR": 15,
    "NEH": 16, "EST": 17, "JOB": 18, "PSA": 19, "PRO": 20,
    "ECC": 21, "SNG": 22, "ISA": 23, "JER": 24, "LAM": 25,
    "EZK": 26, "DAN": 27, "HOS": 28, "JOL": 29, "AMO": 30,
    "OBA": 31, "JON": 32, "MIC": 33, "NAM": 34, "HAB": 35,
    "ZEP": 36, "HAG": 37, "ZEC": 38, "MAL": 39,
    "MAT": 40, "MRK": 41, "LUK": 42, "JHN": 43, "ACT": 44,
    "ROM": 45, "1CO": 46, "2CO": 47, "GAL": 48, "EPH": 49,
    "PHP": 50, "COL": 51, "1TH": 52, "2TH": 53, "1TI": 54,
    "2TI": 55, "TIT": 56, "PHM": 57, "HEB": 58, "JAS": 59,
    "1PE": 60, "2PE": 61, "1JN": 62, "2JN": 63, "3JN": 64,
    "JUD": 65, "REV": 66,
    # Common alternates
    "SOS": 22, "EZE": 26, "NAH": 34, "MRK": 41, "MK": 41,
    "JAS": 59, "JUDE": 65,
}

BOOK_NAMES_TO_NUM: dict[str, int] = {
    "genesis": 1, "exodus": 2, "leviticus": 3, "numbers": 4, "deuteronomy": 5,
    "joshua": 6, "judges": 7, "ruth": 8, "1 samuel": 9, "2 samuel": 10,
    "1 kings": 11, "2 kings": 12, "1 chronicles": 13, "2 chronicles": 14,
    "ezra": 15, "nehemiah": 16, "esther": 17, "job": 18, "psalms": 19,
    "psalm": 19, "proverbs": 20, "ecclesiastes": 21, "song of solomon": 22,
    "song of songs": 22, "isaiah": 23, "jeremiah": 24, "lamentations": 25,
    "ezekiel": 26, "daniel": 27, "hosea": 28, "joel": 29, "amos": 30,
    "obadiah": 31, "jonah": 32, "micah": 33, "nahum": 34, "habakkuk": 35,
    "zephaniah": 36, "haggai": 37, "zechariah": 38, "malachi": 39,
    "matthew": 40, "mark": 41, "luke": 42, "john": 43, "acts": 44,
    "romans": 45, "1 corinthians": 46, "2 corinthians": 47, "galatians": 48,
    "ephesians": 49, "philippians": 50, "colossians": 51,
    "1 thessalonians": 52, "2 thessalonians": 53,
    "1 timothy": 54, "2 timothy": 55, "titus": 56, "philemon": 57,
    "hebrews": 58, "james": 59, "1 peter": 60, "2 peter": 61,
    "1 john": 62, "2 john": 63, "3 john": 64, "jude": 65, "revelation": 66,
}


def resolve_book(ref: str) -> int | None:
    ref = ref.strip()
    if ref.isdigit():
        n = int(ref)
        return n if 1 <= n <= 66 else None
    upper = ref.upper()
    if upper in USFM_TO_NUM:
        return USFM_TO_NUM[upper]
    lower = ref.lower()
    if lower in BOOK_NAMES_TO_NUM:
        return BOOK_NAMES_TO_NUM[lower]
    return None


def create_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verses (
            book    INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse   INTEGER NOT NULL,
            text    TEXT    NOT NULL,
            PRIMARY KEY (book, chapter, verse)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bcv ON verses(book, chapter, verse)")
    conn.commit()
    return conn


def import_csv(fh, conn: sqlite3.Connection, delimiter: str = ",") -> int:
    reader = csv.reader(fh, delimiter=delimiter)
    rows = []
    skipped = 0
    col_offset = 0  # set to 1 if first column is a sequential id (scrollmapper format)
    first_data_row = True
    for line in reader:
        if not line:
            continue
        # Auto-detect scrollmapper format: id,b,c,v,t (5 columns, first col is "id" or integer > 66)
        if first_data_row and len(line) >= 5:
            if line[0].lower() in ("id", "#"):
                col_offset = 1  # header row with id prefix
                first_data_row = False
                continue
            try:
                if int(line[0]) > 66:  # sequential verse id, not a book number
                    col_offset = 1
            except ValueError:
                pass
            first_data_row = False
        if len(line) < 4 + col_offset:
            continue
        b_raw, c_raw, v_raw, text = line[col_offset], line[col_offset+1], line[col_offset+2], line[col_offset+3]
        # Skip header rows
        if b_raw.lower() in ("b", "book", "book_num", "#"):
            continue
        book_num = resolve_book(b_raw)
        if book_num is None:
            skipped += 1
            continue
        try:
            rows.append((book_num, int(c_raw), int(v_raw), text.strip()))
        except ValueError:
            skipped += 1
    conn.executemany(
        "INSERT OR REPLACE INTO verses (book, chapter, verse, text) VALUES (?,?,?,?)", rows
    )
    conn.commit()
    if skipped:
        print(f"  skipped {skipped} unparseable rows", file=sys.stderr)
    return len(rows)


def import_vpl(fh, conn: sqlite3.Connection) -> int:
    """
    Verse-per-line format: BOOKCODE CHAPTER:VERSE text
    e.g. GEN 1:1 In the beginning...
    """
    pattern = re.compile(r"^(\S+)\s+(\d+):(\d+)\s+(.+)$")
    rows = []
    skipped = 0
    for line in fh:
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if not m:
            skipped += 1
            continue
        book_num = resolve_book(m.group(1))
        if book_num is None:
            skipped += 1
            continue
        rows.append((book_num, int(m.group(2)), int(m.group(3)), m.group(4).strip()))

    conn.executemany(
        "INSERT OR REPLACE INTO verses (book, chapter, verse, text) VALUES (?,?,?,?)", rows
    )
    conn.commit()
    if skipped:
        print(f"  skipped {skipped} unparseable rows", file=sys.stderr)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a Bible translation into writ.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage")[1] if "Usage" in __doc__ else "",
    )
    parser.add_argument("file",   help="Input file path")
    parser.add_argument("-n", "--name",   required=True, help="Translation name (e.g. web, kjv)")
    parser.add_argument("-f", "--format", choices=["csv", "tsv", "vpl"], default="csv",
                        help="Input format (default: csv)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory (default: ~/.local/share/writ/translations/)")
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        print(f"error: file not found: {src}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output) if args.output else (
        Path(os.environ.get("WRIT_DATA", Path.home() / ".local" / "share" / "writ"))
        / "translations"
    )
    db_path = out_dir / f"{args.name.lower()}.db"

    print(f"importing '{src}' → {db_path} (format: {args.format})")
    conn = create_db(db_path)

    with open(src, encoding="utf-8", newline="") as fh:
        if args.format in ("csv", "tsv"):
            delim = "\t" if args.format == "tsv" else ","
            count = import_csv(fh, conn, delimiter=delim)
        else:
            count = import_vpl(fh, conn)

    conn.close()
    print(f"done — {count:,} verses written to {db_path}")


if __name__ == "__main__":
    main()
