#!/usr/bin/env python3
"""
writ — lightning-fast terminal Bible reference tool.

Default invocation:   writ <book> [chapter] [verses] [-t translation]
Example:              writ ge 1 1-3
                      writ jn 3 16 -t kjv
                      writ ps 23
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.prompt import Confirm, Prompt

from .books import BOOKS, book_by_number, resolve_book
from .bookmarks import add_bookmark, get_bookmark, list_bookmarks, remove_bookmark
from .daily import get_daily_ref
from .db import get_app_db, get_state, list_translations, set_state
from .display import (
    chapter_prompt,
    console,
    display_bookmark_tree,
    display_comparison,
    display_history,
    display_notes,
    display_search_results,
    display_verses,
    display_verses_with_notes,
    fmt_ref,
    print_error,
    print_info,
    print_success,
)
from .history import get_history, get_last_position, get_reading_streak, record
from .lookup import fetch_verses, get_chapter_count, get_default_translation, get_random_verse
from .notes import get_note, get_notes_for_chapter, list_notes, remove_note, upsert_note
from .plans import (
    days_behind,
    get_active_plan,
    get_catchup_entries,
    get_next_entry,
    get_plan_progress,
    list_plans,
    load_plan,
    mark_entry_done,
    reset_plan_to_today,
    set_active_plan,
)
from .search import search_text

app = typer.Typer(
    name="writ",
    help="Lightning-fast terminal Bible reference and reading tool.",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=True,
    rich_markup_mode="rich",
)

bookmark_app = typer.Typer(help="Manage bookmarks.", no_args_is_help=True)
plan_app     = typer.Typer(help="Manage reading plans.", no_args_is_help=True)
note_app     = typer.Typer(help="Manage verse margin notes.", no_args_is_help=True)

app.add_typer(bookmark_app, name="bookmark")
app.add_typer(bookmark_app, name="bm")
app.add_typer(plan_app,     name="plan")
app.add_typer(note_app,     name="note")


# ── Shared helpers ─────────────────────────────────────────────────────────

def _tr(translation: str | None) -> str:
    return translation.lower() if translation else get_default_translation()


def _save_context(translation: str, book_num: int, chapter: int, verse: int) -> None:
    conn = get_app_db()
    set_state(conn, "last_translation", translation)
    set_state(conn, "last_book",        str(book_num))
    set_state(conn, "last_chapter",     str(chapter))
    set_state(conn, "last_verse",       str(verse))
    conn.close()


def _load_context() -> tuple[str, int, int, int] | None:
    conn = get_app_db()
    tr   = get_state(conn, "last_translation", "")
    book = get_state(conn, "last_book",        "0")
    ch   = get_state(conn, "last_chapter",     "0")
    vs   = get_state(conn, "last_verse",       "1")
    conn.close()
    if not tr or book == "0":
        return None
    return tr, int(book), int(ch), int(vs)


def _interactive_chapter(translation: str, book_num: int, start_chapter: int) -> None:
    """Display a chapter with [n]ext/[p]rev/[b]ookmark/[+]note/[q]uit navigation."""
    book = book_by_number(book_num)
    if not book:
        print_error(f"Invalid book number: {book_num}")
        raise typer.Exit(1)

    chapter = start_chapter
    max_ch = get_chapter_count(translation, book)
    verses: list = []
    needs_redraw = True

    while True:
        if needs_redraw:
            max_ch = get_chapter_count(translation, book)
            verses = fetch_verses(translation, book, chapter)
            if not verses:
                print_error(f"No text found for {book.name} {chapter} in {translation.upper()}.")
                raise typer.Exit(1)

            chapter_notes = get_notes_for_chapter(book_num, chapter)
            if chapter_notes:
                display_verses_with_notes(verses, translation, chapter_notes)
            else:
                display_verses(verses, translation)

            record(translation, book_num, chapter)
            _save_context(translation, book_num, chapter, verses[0].verse)
            needs_redraw = False

        choice = chapter_prompt(book, chapter, max_ch)

        if choice == "n" and chapter < max_ch:
            chapter += 1
            needs_redraw = True
        elif choice == "p" and chapter > 1:
            chapter -= 1
            needs_redraw = True
        elif choice == "b":
            path = Prompt.ask("  bookmark path (e.g. devotionals/morning)")
            bm_id = add_bookmark(path, translation, book_num, chapter, verses[0].verse)
            print_success(f"saved bookmark #{bm_id} → {path}")
        elif choice == "+":
            try:
                vnum = int(Prompt.ask("  verse number"))
            except ValueError:
                print_error("invalid verse number")
            else:
                existing = get_note(book_num, chapter, vnum)
                if existing:
                    console.print(f"  [dim italic]existing: {existing}[/dim italic]")
                text = Prompt.ask("  note")
                upsert_note(book_num, chapter, vnum, text)
                print_success("note saved")
        elif choice in ("q", "\x03", "\x1b", ""):
            break


# ── Main lookup (default command) ─────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def lookup(
    ctx: typer.Context,
    translation: Optional[str] = typer.Option(None, "-t", "--translation",
                                               help="Translation to use  (e.g. esv, kjv, web)"),
    compare_with: Optional[str] = typer.Option(None, "-c", "--compare",
                                                help="Compare with extra translation(s), comma-separated"),
) -> None:
    """
    Look up Bible verses.

      writ ge 1 1-3       Genesis 1:1-3\n
      writ jn 3 16        John 3:16\n
      writ ps 23          Psalm 23 (interactive)\n
      writ ge             Genesis ch.1 (interactive)
    """
    if ctx.invoked_subcommand is not None:
        return

    # ctx.args contains positional tokens not consumed by the options above
    args = [a for a in ctx.args if not a.startswith("-")]
    if not args:
        console.print(ctx.get_help())
        return

    book_ref = args[0]
    chapter: Optional[int] = int(args[1]) if len(args) > 1 else None
    verses:  Optional[str] = args[2]       if len(args) > 2 else None

    book = resolve_book(book_ref)
    if not book:
        print_error(f"unknown book '{book_ref}' — try [bold]writ books[/bold] for a list")
        raise typer.Exit(1)

    tr = _tr(translation)

    # ── chapter-level interactive reading ───────────────────────────────────────────────────────
    if verses is None:
        _interactive_chapter(tr, book.number, chapter or 1)
        return

    # ── specific verse(s) ──────────────────────────────────────────────────────────────────────────────────
    verse_list = fetch_verses(tr, book, chapter or 1, verses)
    if not verse_list:
        print_error(
            f"no results for {book.name} {chapter}:{verses} in {tr.upper()}"
        )
        raise typer.Exit(1)

    v_start = verse_list[0].verse
    v_end   = verse_list[-1].verse

    # Show existing note inline if present
    verse_notes = {v: t for v in [v_start] if (t := get_note(book.number, chapter or 1, v))}
    if verse_notes:
        display_verses_with_notes(verse_list, tr, verse_notes)
    else:
        display_verses(verse_list, tr)

    record(tr, book.number, chapter or 1, v_start, v_end)
    _save_context(tr, book.number, chapter or 1, v_start)

    # Optional side-by-side comparison
    if compare_with:
        pairs = [(tr, verse_list)]
        for ctr in compare_with.split(","):
            ctr = ctr.strip()
            pairs.append((ctr, fetch_verses(ctr, book, chapter or 1, verses)))
        display_comparison(pairs)

    # Quick-action bar for verse-level lookups
    console.print("  [bold][b][/bold]ookmark  [bold][+][/bold]note  [bold][q][/bold]uit", end="  ")
    from .display import getch
    choice = getch()
    console.print(choice)

    if choice == "b":
        path = Prompt.ask("  bookmark path")
        bm_id = add_bookmark(path, tr, book.number, chapter or 1, v_start)
        print_success(f"saved bookmark #{bm_id} → {path}")
    elif choice == "+":
        existing = get_note(book.number, chapter or 1, v_start)
        if existing:
            console.print(f"  [dim italic]existing: {existing}[/dim italic]")
        text = Prompt.ask("  note")
        upsert_note(book.number, chapter or 1, v_start, text)
        print_success("note saved")


# ── Reading flow ────────────────────────────────────────────────────────────────────────

@app.command(name="continue", help="Resume active reading plan or last read position.")
def cont(
    translation: Optional[str] = typer.Option(None, "-t", "--translation"),
) -> None:
    plan_name = get_active_plan()
    tr = _tr(translation)

    if plan_name:
        behind = days_behind(plan_name)
        if behind > 0:
            console.print(
                f"[yellow]You are {behind} day(s) behind on '[bold]{plan_name}[/bold]'.[/yellow]"
            )
            choice = Prompt.ask(
                "  [c]atch up today  [r]eset to today  [k]eep going from where you left off",
                choices=["c", "r", "k"],
                default="k",
            )
            if choice == "r":
                reset_plan_to_today(plan_name)
                print_success("plan reset to today")
            elif choice == "c":
                for entry in get_catchup_entries(plan_name):
                    _read_plan_entry(tr, entry)
                return

        entry = get_next_entry(plan_name)
        if not entry:
            console.print(f"[green]Plan '[bold]{plan_name}[/bold]' is complete![/green]")
            return
        _read_plan_entry(tr, entry, prompt_done=True)

    else:
        pos = get_last_position()
        if not pos:
            print_info("no history yet — try: writ ge 1")
            return
        console.print(f"[dim]resuming {pos['book_name']} {pos['chapter']}[/dim]")
        _interactive_chapter(tr or pos["translation"], pos["book"], pos["chapter"])


def _read_plan_entry(tr: str, entry: dict, prompt_done: bool = False) -> None:
    book = book_by_number(entry["book"])
    if not book:
        return
    label = f"{entry['book_name']} {entry['chapter_start']}"
    if entry["chapter_end"] != entry["chapter_start"]:
        label += f"-{entry['chapter_end']}"
    console.print(f"[dim]Day {entry['day']} — {label}[/dim]")

    for ch in range(entry["chapter_start"], entry["chapter_end"] + 1):
        _interactive_chapter(tr, book.number, ch)

    if prompt_done and Confirm.ask("  mark as done and advance?", default=True):
        mark_entry_done(entry["id"])
        nxt = get_next_entry(entry.get("plan_name", ""))  # best-effort
        if nxt:
            print_success(f"done! next: {nxt['book_name']} {nxt['chapter_start']}")
        else:
            print_success("plan complete!")


@app.command()
def done() -> None:
    """Mark current plan entry done and advance."""
    plan_name = get_active_plan()
    if not plan_name:
        print_error("no active plan — set one with: writ plan set <name>")
        raise typer.Exit(1)
    entry = get_next_entry(plan_name)
    if not entry:
        console.print(f"[green]Plan '[bold]{plan_name}[/bold]' is complete![/green]")
        return
    mark_entry_done(entry["id"])
    nxt = get_next_entry(plan_name)
    if nxt:
        print_success(f"done! next: {nxt['book_name']} {nxt['chapter_start']}")
    else:
        print_success("plan complete!")


# ── Discovery commands ────────────────────────────────────────────────────────────────────────

@app.command()
def daily(
    translation: Optional[str] = typer.Option(None, "-t", "--translation"),
) -> None:
    """Show today's verse of the day."""
    ref = get_daily_ref()
    if not ref:
        print_error("daily_verses.txt not found in data/")
        raise typer.Exit(1)

    book_abbrev, chapter, verse = ref
    book = resolve_book(book_abbrev)
    if not book:
        print_error(f"bad entry in daily_verses.txt: '{book_abbrev}'")
        raise typer.Exit(1)

    tr = _tr(translation)
    verse_list = fetch_verses(tr, book, chapter, str(verse))
    if verse_list:
        console.print("[bold dim]— Verse of the Day —[/bold dim]")
        display_verses(verse_list, tr)


@app.command(name="random")
def random_verse(
    book_ref: Optional[str]  = typer.Argument(None, help="Limit to a specific book"),
    translation: Optional[str] = typer.Option(None, "-t", "--translation"),
) -> None:
    """Display a random verse (optionally from one book)."""
    tr = _tr(translation)
    book = None
    if book_ref:
        book = resolve_book(book_ref)
        if not book:
            print_error(f"unknown book '{book_ref}'")
            raise typer.Exit(1)

    verse = get_random_verse(tr, book)
    if not verse:
        print_error(f"no verses found in {tr.upper()}")
        raise typer.Exit(1)
    display_verses([verse], tr)


@app.command()
def search(
    query:       str            = typer.Argument(..., help="Text to search for"),
    translation: Optional[str]  = typer.Option(None, "-t", "--translation"),
    book_ref:    Optional[str]  = typer.Option(None, "-b", "--book", help="Limit to one book"),
) -> None:
    """Full-text search across a translation."""
    tr = _tr(translation)
    book_num = None
    if book_ref:
        b = resolve_book(book_ref)
        if not b:
            print_error(f"unknown book '{book_ref}'")
            raise typer.Exit(1)
        book_num = b.number

    results = search_text(tr, query, book_num)
    if not results:
        print_info(f"no results for '{query}' in {tr.upper()}")
        return
    console.print(f"[dim]{len(results)} result(s) for '[bold]{query}[/bold]' in {tr.upper()}[/dim]\n")
    display_search_results(results)


@app.command()
def compare(
    book_ref:     str = typer.Argument(..., help="Book abbreviation"),
    chapter:      int = typer.Argument(...),
    verse_spec:   str = typer.Argument(..., help="Verse spec  (e.g. 16 or 1-3)"),
    translations: str = typer.Argument(..., help="Comma-separated translations  (e.g. esv,kjv,web)"),
) -> None:
    """Compare a passage across multiple translations side by side."""
    book = resolve_book(book_ref)
    if not book:
        print_error(f"unknown book '{book_ref}'")
        raise typer.Exit(1)

    pairs = []
    for tr in translations.split(","):
        tr = tr.strip()
        pairs.append((tr, fetch_verses(tr, book, chapter, verse_spec)))
    display_comparison(pairs)


# ── First-time setup ───────────────────────────────────────────────────────────────────────────────────

@app.command()
def setup() -> None:
    """Download and install the King James Bible as the default translation."""
    import urllib.request
    import csv
    import sqlite3 as _sqlite3

    from .db import TRANSLATIONS_DIR, get_app_db, set_state, ensure_dirs

    # scrollmapper/bible_databases — formats/csv/ layout, Book,Chapter,Verse,Text columns
    KJV_URLS = [
        "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/KJV.csv",
        "https://raw.githubusercontent.com/scrollmapper/bible_databases/main/formats/csv/KJV.csv",
    ]

    ensure_dirs()
    db_path = TRANSLATIONS_DIR / "kjv.db"

    if db_path.exists():
        if not Confirm.ask(
            "  [yellow]kjv.db already exists.[/yellow] Re-download and overwrite?",
            default=False,
        ):
            print_info("skipped — run 'writ set translation kjv' if not already set")
            return

    console.print("[dim]Downloading King James Bible from scrollmapper/bible_databases…[/dim]")

    raw = None
    last_err = ""
    for url in KJV_URLS:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            break
        except Exception as exc:
            last_err = str(exc)
            continue

    if raw is None:
        print_error(f"download failed: {last_err}")
        console.print(
            "  You can import a Bible CSV manually:\n"
            "  [dim]python scripts/import_translation.py <file.csv> -n kjv[/dim]"
        )
        raise typer.Exit(1)

    # Parse CSV — format: Book,Chapter,Verse,Text (book name strings)
    rows: list[tuple[int, int, int, str]] = []
    reader = csv.reader(raw.splitlines())
    for line in reader:
        if not line or len(line) < 4:
            continue
        book_raw, c_raw, v_raw, text = line[0].strip(), line[1].strip(), line[2].strip(), line[3].strip()
        if book_raw.lower() in ("book", "b"):
            continue  # header row
        book_obj = resolve_book(book_raw)
        if book_obj is None:
            continue
        try:
            rows.append((book_obj.number, int(c_raw), int(v_raw), text))
        except ValueError:
            continue

    if not rows:
        print_error("CSV parsed but no verses found — format may have changed.")
        raise typer.Exit(1)

    console.print(f"[dim]Writing {len(rows):,} verses to {db_path}…[/dim]")
    conn = _sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS verses "
        "(book INTEGER, chapter INTEGER, verse INTEGER, text TEXT, "
        "PRIMARY KEY (book, chapter, verse))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bcv ON verses(book, chapter, verse)")
    conn.executemany(
        "INSERT OR REPLACE INTO verses (book, chapter, verse, text) VALUES (?,?,?,?)", rows
    )
    conn.commit()
    conn.close()

    app_conn = get_app_db()
    set_state(app_conn, "default_translation", "kjv")
    app_conn.close()

    print_success(f"King James Bible installed ({len(rows):,} verses)")
    print_success("Default translation set to: kjv")
    console.print("\n  You're ready. Try: [bold]writ ge 1[/bold]\n")


# ── Information commands ───────────────────────────────────────────────────────────────────────────────────

@app.command()
def history(
    limit: int = typer.Option(20, "-n", help="Number of entries to show"),
) -> None:
    """Show recent reading history."""
    items = get_history(limit)
    if not items:
        print_info("no history yet")
        return
    streak = get_reading_streak()
    if streak > 1:
        console.print(f"[green]reading streak: {streak} day(s)[/green]\n")
    display_history(items)


@app.command()
def translations() -> None:
    """List installed translations."""
    trs = list_translations()
    if not trs:
        print_info("no translations installed — see README for import instructions")
        return
    conn = get_app_db()
    default = get_state(conn, "default_translation", "kjv")
    conn.close()
    for t in trs:
        marker = "  [green](default)[/green]" if t == default else ""
        console.print(f"  [bold]{t}[/bold]{marker}")


@app.command()
def books() -> None:
    """List all 66 books with their abbreviations."""
    from rich.table import Table

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#",       style="dim",   width=4)
    table.add_column("Book")
    table.add_column("Short",   style="green")
    table.add_column("Also",    style="dim")
    table.add_column("Chs",     style="dim",   justify="right")

    for b in BOOKS:
        table.add_row(
            str(b.number),
            b.name,
            b.abbrevs[0],
            ", ".join(b.abbrevs[1:]),
            str(b.chapters),
        )
    console.print(table)


@app.command(name="set")
def set_config(
    key:   str = typer.Argument(..., help="Setting key  (translation | plan)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a persistent configuration value."""
    key_map = {
        "translation": "default_translation",
        "plan":        "active_plan",
    }
    if key not in key_map:
        print_error(f"unknown key '{key}' — valid: {', '.join(key_map)}")
        raise typer.Exit(1)
    conn = get_app_db()
    set_state(conn, key_map[key], value)
    conn.close()
    print_success(f"{key} = {value}")


# ── Bookmark subcommands ────────────────────────────────────────────────────────────────────────────────

@bookmark_app.callback(invoke_without_command=True)
def _bm_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _bm_list()


@bookmark_app.command(name="add")
def bm_add(
    path:        str           = typer.Argument(..., help="Path  e.g. devotionals/morning"),
    book_ref:    Optional[str] = typer.Argument(None),
    chapter:     Optional[int] = typer.Argument(None),
    verse:       Optional[int] = typer.Argument(None),
    translation: Optional[str] = typer.Option(None, "-t", "--translation"),
) -> None:
    """Bookmark a verse. Omit location to use the last looked-up verse."""
    if book_ref:
        book = resolve_book(book_ref)
        if not book:
            print_error(f"unknown book '{book_ref}'")
            raise typer.Exit(1)
        book_num = book.number
        ch = chapter or 1
        vs = verse or 1
        tr = _tr(translation)
    else:
        ctx = _load_context()
        if not ctx:
            print_error("no recent verse — specify: writ bookmark add <path> <book> <ch> <v>")
            raise typer.Exit(1)
        tr, book_num, ch, vs = ctx
        if translation:
            tr = translation.lower()

    bm_id = add_bookmark(path, tr, book_num, ch, vs)
    b = book_by_number(book_num)
    print_success(f"bookmark #{bm_id}: {b.name if b else book_num} {ch}:{vs} → {path}")


@bookmark_app.command(name="list")
def _bm_list(
    path: Optional[str] = typer.Argument(None, help="Browse a subtree"),
) -> None:
    """List bookmarks as a directory tree."""
    items = list_bookmarks(path)
    if not items:
        print_info("no bookmarks found")
        return
    display_bookmark_tree(items, path)


@bookmark_app.command(name="go")
def bm_go(
    bookmark_id: int           = typer.Argument(...),
    translation: Optional[str] = typer.Option(None, "-t", "--translation"),
) -> None:
    """Jump to a bookmarked verse."""
    bm = get_bookmark(bookmark_id)
    if not bm:
        print_error(f"bookmark #{bookmark_id} not found")
        raise typer.Exit(1)
    tr = _tr(translation) or bm["translation"]
    book = book_by_number(bm["book"])
    if not book:
        print_error("invalid book stored in bookmark")
        raise typer.Exit(1)
    verse_list = fetch_verses(tr, book, bm["chapter"], str(bm["verse"]))
    display_verses(verse_list, tr)


@bookmark_app.command(name="remove")
def bm_remove(
    bookmark_id: int = typer.Argument(...),
) -> None:
    """Remove a bookmark by ID."""
    if remove_bookmark(bookmark_id):
        print_success(f"bookmark #{bookmark_id} removed")
    else:
        print_error(f"bookmark #{bookmark_id} not found")


# ── Note subcommands ────────────────────────────────────────────────────────────────────────────────────

@note_app.command(name="add")
def note_add(
    text:        str           = typer.Argument(..., help="Note text (margin annotation)"),
    book_ref:    Optional[str] = typer.Argument(None),
    chapter:     Optional[int] = typer.Argument(None),
    verse:       Optional[int] = typer.Argument(None),
) -> None:
    """Add a margin note to a verse. Omit location to use the last looked-up verse."""
    if book_ref:
        book = resolve_book(book_ref)
        if not book:
            print_error(f"unknown book '{book_ref}'")
            raise typer.Exit(1)
        book_num, ch, vs = book.number, chapter or 1, verse or 1
    else:
        ctx = _load_context()
        if not ctx:
            print_error("no recent verse — specify: writ note add '<text>' <book> <ch> <v>")
            raise typer.Exit(1)
        _, book_num, ch, vs = ctx

    upsert_note(book_num, ch, vs, text)
    b = book_by_number(book_num)
    print_success(f"note saved on {b.name if b else book_num} {ch}:{vs}")


@note_app.command(name="list")
def note_list(
    book_ref: Optional[str] = typer.Argument(None),
    chapter:  Optional[int] = typer.Argument(None),
) -> None:
    """List margin notes."""
    book_num = None
    if book_ref:
        book = resolve_book(book_ref)
        if not book:
            print_error(f"unknown book '{book_ref}'")
            raise typer.Exit(1)
        book_num = book.number

    items = list_notes(book_num, chapter)
    if not items:
        print_info("no notes found")
        return
    display_notes(items)


@note_app.command(name="remove")
def note_remove(
    book_ref: str = typer.Argument(...),
    chapter:  int = typer.Argument(...),
    verse:    int = typer.Argument(...),
) -> None:
    """Remove a margin note."""
    book = resolve_book(book_ref)
    if not book:
        print_error(f"unknown book '{book_ref}'")
        raise typer.Exit(1)
    if remove_note(book.number, chapter, verse):
        print_success(f"note removed from {book.name} {chapter}:{verse}")
    else:
        print_error("note not found")


# ── Plan subcommands ────────────────────────────────────────────────────────────────────────────────────

@plan_app.command(name="load")
def plan_load(
    filepath: str           = typer.Argument(..., help="Path to .txt plan file"),
    name:     Optional[str] = typer.Option(None, "-n", "--name",
                                            help="Plan name (defaults to filename stem)"),
) -> None:
    """Import a reading plan from a .txt file."""
    from pathlib import Path
    p = Path(filepath)
    if not p.exists():
        print_error(f"file not found: {filepath}")
        raise typer.Exit(1)
    plan_name = name or p.stem
    count = load_plan(plan_name, p)
    print_success(f"loaded plan '[bold]{plan_name}[/bold]' with {count} entries")
    if Confirm.ask(f"  set '{plan_name}' as active plan?", default=True):
        set_active_plan(plan_name)


@plan_app.command(name="list")
def plan_list() -> None:
    """List all loaded reading plans."""
    plans = list_plans()
    active = get_active_plan()
    if not plans:
        print_info("no plans loaded — use: writ plan load <file.txt>")
        return
    for p in plans:
        prog = get_plan_progress(p)
        pct  = f"{prog['done'] / prog['total'] * 100:.0f}%" if prog["total"] else "—"
        marker = "  [green](active)[/green]" if p == active else ""
        console.print(
            f"  [bold]{p}[/bold]{marker}  "
            f"[dim]{prog['done']}/{prog['total']}  {pct}[/dim]"
        )


@plan_app.command(name="set")
def plan_set(name: str = typer.Argument(...)) -> None:
    """Set the active reading plan."""
    if name not in list_plans():
        print_error(f"plan '{name}' not found — use 'writ plan list'")
        raise typer.Exit(1)
    set_active_plan(name)
    print_success(f"active plan: {name}")


@plan_app.command(name="status")
def plan_status() -> None:
    """Show current plan progress and next entry."""
    plan_name = get_active_plan()
    if not plan_name:
        print_info("no active plan — set one with: writ plan set <name>")
        return
    prog  = get_plan_progress(plan_name)
    entry = get_next_entry(plan_name)
    pct   = f"{prog['done'] / prog['total'] * 100:.0f}%" if prog["total"] else "—"

    console.print(f"  [bold]{plan_name}[/bold]")
    console.print(f"  progress: {prog['done']}/{prog['total']}  ({pct})")
    if entry:
        nxt = f"{entry['book_name']} {entry['chapter_start']}"
        if entry["chapter_end"] != entry["chapter_start"]:
            nxt += f"-{entry['chapter_end']}"
        console.print(f"  next: [green]{nxt}[/green]  (day {entry['day']})")
        if entry.get("target_date"):
            console.print(f"  target date: [dim]{entry['target_date']}[/dim]")
    else:
        console.print("  [green]complete![/green]")


# Click's MultiCommand.parse_args always routes the first positional token into
# ctx._protected_args (the would-be subcommand slot), then Group.invoke calls
# resolve_command on it, which raises "No such command" for book abbreviations
# like 'ge'.  The fix: patch the specific Click group's parse_args so that tokens
# not matching a registered subcommand bypass _protected_args and land in
# ctx.args instead, where our callback reads them via ctx.args.
import typer.main as _typer_main  # noqa: E402
import click as _click             # noqa: E402

_orig_get_command = _typer_main.get_command


def _get_command_patched(typer_instance, *a, **kw):
    cmd = _orig_get_command(typer_instance, *a, **kw)
    if typer_instance is not app:
        return cmd

    _known = cmd.commands  # dict populated by get_command

    def _parse_args(ctx: _click.Context, args: list) -> list:
        # Let Click parse the group's own options (-t, -c, etc.)
        rest = _click.Command.parse_args(cmd, ctx, args)
        if rest:
            first = rest[0]
            if first in _known:
                # Known subcommand — normal routing
                ctx._protected_args, ctx.args = rest[:1], rest[1:]
            else:
                # Unknown token (book ref, etc.) — pass all to callback via ctx.args
                ctx._protected_args = []
                ctx.args = rest
        return ctx.args

    cmd.parse_args = _parse_args
    return cmd


_typer_main.get_command = _get_command_patched
