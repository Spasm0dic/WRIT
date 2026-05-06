from vrs.books import resolve_book, book_by_number, BOOKS


def test_all_66_books_present():
    assert len(BOOKS) == 66


def test_resolve_by_short_abbrev():
    assert resolve_book("ge").name  == "Genesis"
    assert resolve_book("jn").name  == "John"
    assert resolve_book("re").name  == "Revelation"
    assert resolve_book("ps").name  == "Psalms"
    assert resolve_book("1co").name == "1 Corinthians"
    assert resolve_book("2jn").name == "2 John"


def test_resolve_case_insensitive():
    assert resolve_book("GE")  is resolve_book("ge")
    assert resolve_book("JN")  is resolve_book("jn")
    assert resolve_book("1CO") is resolve_book("1co")


def test_resolve_full_name():
    assert resolve_book("genesis").number   == 1
    assert resolve_book("Genesis").number   == 1
    assert resolve_book("revelation").number == 66


def test_resolve_full_name_no_space():
    assert resolve_book("1samuel").number == 9
    assert resolve_book("1john").number   == 62


def test_resolve_unknown():
    assert resolve_book("xyz") is None
    assert resolve_book("")    is None


def test_book_by_number():
    assert book_by_number(1).name  == "Genesis"
    assert book_by_number(66).name == "Revelation"
    assert book_by_number(0)       is None
    assert book_by_number(67)      is None


def test_john_disambiguation():
    jn   = resolve_book("jn")
    one  = resolve_book("1jn")
    two  = resolve_book("2jn")
    three= resolve_book("3jn")
    assert jn.number    == 43
    assert one.number   == 62
    assert two.number   == 63
    assert three.number == 64


def test_no_duplicate_canonical_abbrevs():
    seen = {}
    for book in BOOKS:
        canon = book.abbrevs[0]
        assert canon not in seen, f"Duplicate canonical abbrev '{canon}'"
        seen[canon] = book.name


def test_parse_verse_spec():
    from vrs.lookup import parse_verse_spec
    assert parse_verse_spec("1")     == [(1, 1)]
    assert parse_verse_spec("1-3")   == [(1, 3)]
    assert parse_verse_spec("1,5")   == [(1, 1), (5, 5)]
    assert parse_verse_spec("1-3,5") == [(1, 3), (5, 5)]
