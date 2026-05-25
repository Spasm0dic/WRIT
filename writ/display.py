import sys
import tty
import termios

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.table import Table

from .books import Book
from .lookup import Verse

console = Console()


# ── Single-character input ────────────────────────────────────────────────────

def getch() -> str:
    """Read one character without requiring Enter. Falls back to line input."""
    if not sys.stdin.isatty():
        return sys.stdin.readline().strip()[:1] or "q"
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


# ── Reference formatting ──────────────────────────────────────────────────────

def fmt_ref(
    book: Book,
    chapter: int,
    verse_start: int | None = None,
    verse_end: int | None = None,
) -> str:
    ref = f"{book.name} {chapter}"
    if verse_start is not None:
        ref += f":{verse_start}"
        if verse_end is not None and verse_end != verse_start:
            ref += f"-{verse_end}"
    return ref


# ── Verse display ─────────────────────────────────────────────────────────────

def display_verses(verses: list[Verse], translation: str) -> None:
    if not verses:
        console.print("[yellow]No verses found.[/yellow]")
        return

    book = verses[0].book
    chapter = verses[0].chapter
    v_start = verses[0].verse
    v_end = verses[-1].verse

    is_full_chapter = (v_end - v_start + 1) == len(verses) and v_start == 1
    ref = fmt_ref(book, chapter) if is_full_chapter and len(verses) > 5 else fmt_ref(book, chapter, v_start, v_end if v_end != v_start else None)

    body = Text()
    for v in verses:
        body.append(f"{v.verse} ", style="bold dim")
        body.append(v.text.strip())
        body.append("\n")

    console.print(Panel(
        body,
        title=f"[bold]{ref}[/bold]",
        subtitle=f"[dim]{translation.upper()}[/dim]",
        border_style="blue",
        padding=(0, 1),
    ))


def display_verses_with_notes(verses: list[Verse], translation: str, notes: dict[int, str]) -> None:
    """Display verses and inline any margin notes after their verse."""
    if not verses:
        console.print("[yellow]No verses found.[/yellow]")
        return

    book = verses[0].book
    chapter = verses[0].chapter
    v_start = verses[0].verse
    v_end = verses[-1].verse
    ref = fmt_ref(book, chapter, v_start, v_end if v_end != v_start else None)

    body = Text()
    for v in verses:
        body.append(f"{v.verse} ", style="bold dim")
        body.append(v.text.strip())
        body.append("\n")
        if v.verse in notes:
            body.append(f"   ✎ {notes[v.verse]}\n", style="italic dim yellow")

    console.print(Panel(
        body,
        title=f"[bold]{ref}[/bold]",
        subtitle=f"[dim]{translation.upper()}[/dim]",
        border_style="blue",
        padding=(0, 1),
    ))


# ── Chapter navigation prompt ─────────────────────────────────────────────────

def chapter_prompt(book: Book, chapter: int, max_chapter: int) -> str:
    """Render nav bar and return a single-char choice."""
    bar = Text("  ")
    if chapter > 1:
        bar.append("[p]", style="bold")
        bar.append("rev  ")
    if chapter < max_chapter:
        bar.append("[n]", style="bold")
        bar.append("ext  ")
    bar.append("[b]", style="bold")
    bar.append("ookmark  ")
    bar.append("[+]", style="bold")
    bar.append("note  ")
    bar.append("[q]", style="bold")
    bar.append("uit")
    console.print(bar, end="")
    ch = getch()
    console.print()
    return ch.lower()


# ── Comparison display ────────────────────────────────────────────────────────

def display_comparison(verse_sets: list[tuple[str, list[Verse]]]) -> None:
    if not verse_sets:
        return

    all_verse_nums: set[int] = set()
    for _, verses in verse_sets:
        for v in verses:
            all_verse_nums.add(v.verse)

    table = Table(show_header=True, header_style="bold blue", padding=(0, 1), expand=True)
    for tr, _ in verse_sets:
        table.add_column(tr.upper(), ratio=1, overflow="fold")

    for vnum in sorted(all_verse_nums):
        row = []
        for _, verses in verse_sets:
            match = next((v for v in verses if v.verse == vnum), None)
            cell = Text()
            cell.append(f"{vnum} ", style="bold dim")
            cell.append(match.text.strip() if match else "[dim]—[/dim]")
            row.append(cell)
        table.add_row(*row)

    console.print(table)


# ── Bookmark tree ─────────────────────────────────────────────────────────────

def display_bookmark_tree(items: list[dict], path_filter: str | None = None) -> None:
    root_label = f"[bold blue]bookmarks[/bold blue]"
    if path_filter:
        root_label += f"[dim]/{path_filter.strip('/')}[/dim]"
    tree = Tree(root_label)
    nodes: dict[str, Tree] = {}

    for item in sorted(items, key=lambda x: x["path"]):
        parts = item["path"].strip("/").split("/")
        current = tree
        current_path = ""

        for i, segment in enumerate(parts[:-1]):
            current_path = "/".join(parts[: i + 1])
            if current_path not in nodes:
                nodes[current_path] = current.add(f"[blue]{segment}/[/blue]")
            current = nodes[current_path]

        ref = f"{item['book_name']} {item['chapter']}:{item['verse']}"
        leaf_label = (
            f"[green]{parts[-1]}[/green]  "
            f"[dim]{ref}  #{item['id']}  {item['translation'].upper()}[/dim]"
        )
        current.add(leaf_label)

    console.print(tree)


# ── Search results ────────────────────────────────────────────────────────────

def display_search_results(results: list[dict]) -> None:
    for r in results:
        ref = f"{r['book_name']} {r['chapter']}:{r['verse']}"
        console.print(f"  [bold]{ref}[/bold]  [dim]{r['translation'].upper()}[/dim]")
        console.print(f"    {r['text'].strip()}\n")


# ── History ───────────────────────────────────────────────────────────────────

def display_history(items: list[dict]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Reference")
    table.add_column("Translation", style="dim")
    table.add_column("When", style="dim")

    for i, item in enumerate(items, 1):
        ref = f"{item['book_name']} {item['chapter']}"
        if item["verse_start"]:
            ref += f":{item['verse_start']}"
            if item["verse_end"] and item["verse_end"] != item["verse_start"]:
                ref += f"-{item['verse_end']}"
        table.add_row(str(i), ref, item["translation"].upper(), item["accessed_at"])

    console.print(table)


# ── Notes list ────────────────────────────────────────────────────────────────

def display_notes(items: list[dict]) -> None:
    for item in items:
        ref = f"[bold]{item['book_name']} {item['chapter']}:{item['verse']}[/bold]"
        console.print(f"  {ref}")
        console.print(f"    [italic dim]{item['text']}[/italic dim]\n")


# ── Helpers ───────────────────────────────────────────────────────────────────

def print_error(msg: str) -> None:
    console.print(f"[red]error:[/red] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")


def print_success(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")
