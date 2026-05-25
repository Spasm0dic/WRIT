from dataclasses import dataclass


@dataclass
class Book:
    number: int
    name: str
    abbrevs: list[str]   # first entry is the canonical short form
    chapters: int


BOOKS: list[Book] = [
    # ── Old Testament ────────────────────────────────────────────────────────
    Book(1,  "Genesis",          ["ge",   "gen"],          50),
    Book(2,  "Exodus",           ["ex",   "exo"],          40),
    Book(3,  "Leviticus",        ["le",   "lev"],          27),
    Book(4,  "Numbers",          ["nu",   "num"],          36),
    Book(5,  "Deuteronomy",      ["de",   "dt",  "deu"],   34),
    Book(6,  "Joshua",           ["jos",  "josh"],         24),
    Book(7,  "Judges",           ["jdg",  "judg"],         21),
    Book(8,  "Ruth",             ["ru",   "rth"],           4),
    Book(9,  "1 Samuel",         ["1sa",  "1sam"],         31),
    Book(10, "2 Samuel",         ["2sa",  "2sam"],         24),
    Book(11, "1 Kings",          ["1ki",  "1kin"],         22),
    Book(12, "2 Kings",          ["2ki",  "2kin"],         25),
    Book(13, "1 Chronicles",     ["1ch",  "1chr"],         29),
    Book(14, "2 Chronicles",     ["2ch",  "2chr"],         36),
    Book(15, "Ezra",             ["ezr",  "ezra"],         10),
    Book(16, "Nehemiah",         ["ne",   "neh"],          13),
    Book(17, "Esther",           ["es",   "est"],          10),
    Book(18, "Job",              ["job"],                  42),
    Book(19, "Psalms",           ["ps",   "psa"],         150),
    Book(20, "Proverbs",         ["pr",   "pro",  "prv"],  31),
    Book(21, "Ecclesiastes",     ["ec",   "ecc"],          12),
    Book(22, "Song of Solomon",  ["so",   "ss",   "sng"],   8),
    Book(23, "Isaiah",           ["is",   "isa"],          66),
    Book(24, "Jeremiah",         ["je",   "jer"],          52),
    Book(25, "Lamentations",     ["la",   "lam"],           5),
    Book(26, "Ezekiel",          ["eze",  "ezk"],          48),
    Book(27, "Daniel",           ["da",   "dan"],          12),
    Book(28, "Hosea",            ["ho",   "hos"],          14),
    Book(29, "Joel",             ["joe",  "jol"],           3),
    Book(30, "Amos",             ["am",   "amo"],           9),
    Book(31, "Obadiah",          ["ob",   "oba"],           1),
    Book(32, "Jonah",            ["jon",  "jnh"],           4),
    Book(33, "Micah",            ["mic",  "mch"],           7),
    Book(34, "Nahum",            ["na",   "nah"],           3),
    Book(35, "Habakkuk",         ["hab",  "hbk"],           3),
    Book(36, "Zephaniah",        ["zep",  "zph"],           3),
    Book(37, "Haggai",           ["hag",  "hgg"],           2),
    Book(38, "Zechariah",        ["zec",  "zch"],          14),
    Book(39, "Malachi",          ["mal",  "mlc"],           4),
    # ── New Testament ────────────────────────────────────────────────────────
    Book(40, "Matthew",          ["mt",   "mat"],          28),
    Book(41, "Mark",             ["mk",   "mar"],          16),
    Book(42, "Luke",             ["lu",   "luk"],          24),
    Book(43, "John",             ["jn",   "joh"],          21),
    Book(44, "Acts",             ["ac",   "act"],          28),
    Book(45, "Romans",           ["ro",   "rom"],          16),
    Book(46, "1 Corinthians",    ["1co",  "1cor"],         16),
    Book(47, "2 Corinthians",    ["2co",  "2cor"],         13),
    Book(48, "Galatians",        ["ga",   "gal"],           6),
    Book(49, "Ephesians",        ["eph",  "eps"],           6),
    Book(50, "Philippians",      ["php",  "phl"],           4),
    Book(51, "Colossians",       ["col",  "cls"],           4),
    Book(52, "1 Thessalonians",  ["1th",  "1ths"],          5),
    Book(53, "2 Thessalonians",  ["2th",  "2ths"],          3),
    Book(54, "1 Timothy",        ["1ti",  "1tim"],          6),
    Book(55, "2 Timothy",        ["2ti",  "2tim"],          4),
    Book(56, "Titus",            ["tit",  "tts"],           3),
    Book(57, "Philemon",         ["phm",  "phmo"],          1),
    Book(58, "Hebrews",          ["heb",  "hbr"],          13),
    Book(59, "James",            ["jas",  "jms"],           5),
    Book(60, "1 Peter",          ["1pe",  "1pet"],          5),
    Book(61, "2 Peter",          ["2pe",  "2pet"],          3),
    Book(62, "1 John",           ["1jn",  "1jo"],           5),
    Book(63, "2 John",           ["2jn",  "2jo"],           1),
    Book(64, "3 John",           ["3jn",  "3jo"],           1),
    Book(65, "Jude",             ["jude", "jud"],           1),
    Book(66, "Revelation",       ["re",   "rev"],          22),
]

# Build lookup index: all abbreviations + full lowercase names → Book
_index: dict[str, Book] = {}
for _b in BOOKS:
    _index[_b.name.lower()] = _b
    for _a in _b.abbrevs:
        _index[_a.lower()] = _b

# Also index without spaces for numbered books ("1samuel", "1sam", etc.)
for _b in BOOKS:
    _index[_b.name.lower().replace(" ", "")] = _b


def resolve_book(ref: str) -> Book | None:
    """Resolve an abbreviation or full name to a Book, case-insensitive."""
    return _index.get(ref.strip().lower())


def book_by_number(n: int) -> Book | None:
    if 1 <= n <= 66:
        return BOOKS[n - 1]
    return None
