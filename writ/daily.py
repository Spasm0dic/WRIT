from datetime import date
from pathlib import Path

_DAILY_FILE = Path(__file__).parent.parent / "data" / "daily_verses.txt"


def _load_refs() -> list[tuple[str, int, int]]:
    if not _DAILY_FILE.exists():
        return []
    refs = []
    with open(_DAILY_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    refs.append((parts[0], int(parts[1]), int(parts[2])))
                except ValueError:
                    continue
    return refs


def get_daily_ref() -> tuple[str, int, int] | None:
    """Return (book_abbrev, chapter, verse) deterministically based on day-of-year."""
    refs = _load_refs()
    if not refs:
        return None
    idx = date.today().timetuple().tm_yday % len(refs)
    return refs[idx]
