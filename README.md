# writ

Lightning-fast terminal Bible reference and reading tool.  
Offline-first, no account required, cyberdeck-friendly.

```
writ ge 1 1-3          # Genesis 1:1-3
writ jn 3 16           # John 3:16, interactive
writ ps 23             # Psalm 23, chapter navigation
writ daily             # verse of the day
writ continue          # resume active reading plan
```

---

## Install

One command — no pip, no system packages beyond Python 3.10:

```bash
curl -fsSL https://raw.githubusercontent.com/Spasm0dic/WRIT/main/install.sh | bash
```

This will:
1. Create a Python virtualenv at `~/.local/share/writ/env`
2. Install `writ` into that venv
3. Symlink `writ` to `~/.local/bin/writ`
4. Add `~/.local/bin` to your PATH if needed
5. Download and install the World English Bible (public domain)

After install, open a new terminal or run `source ~/.bashrc` and you're ready:

```bash
writ ge 1
```

**Requirements:** Python 3.10+, internet access for the initial translation download.

---

## Translations

`writ setup` (run automatically on install) downloads the **World English Bible** — fully public domain, no license restrictions.

To add more translations, use the bundled importer:

```bash
python scripts/import_translation.py file.csv -n kjv --format csv
writ set translation kjv
```

**Supported input formats:**

| Format | Flag | Example |
|--------|------|-------|
| CSV    | `--format csv` | `book,chapter,verse,text` |
| TSV    | `--format tsv` | `book\tchapter\tverse\ttext` |
| VPL    | `--format vpl` | `GEN 1:1 In the beginning...` |

Also auto-detects the [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) CSV format (`id,b,c,v,t`).

---

## Commands

### Lookup (default)

```
writ <book> [chapter] [verses] [-t translation] [-c compare]

writ ge                   # Genesis ch.1, interactive nav
writ ge 1                 # Genesis 1, interactive nav
writ ge 1 1               # Genesis 1:1
writ ge 1 1-3             # Genesis 1:1-3
writ ro 8 28,35           # Romans 8:28 and 8:35
writ ge 1 1 -t kjv        # specific translation
writ ge 1 1 -c kjv        # side-by-side comparison with KJV
```

After displaying a verse, a quick-action bar appears:
`[b]ookmark  [+]note  [q]uit`

During chapter reading:
`[p]rev  [n]ext  [b]ookmark  [+]note  [q]uit`

### Book abbreviations

All 66 books have canonical short forms. Run `writ books` to see them all.

Key conflict resolutions:

| Short | Book |
|-------|------|
| `jn`  | John |
| `1jn` `2jn` `3jn` | 1–3 John |
| `1sa` `2sa` | 1–2 Samuel |
| `1ki` `2ki` | 1–2 Kings |
| `1co` `2co` | 1–2 Corinthians |
| `ps`  | Psalms |
| `pr`  | Proverbs |

### Reading plans

```bash
writ plan load data/plans/gospels.txt   # import a plan
writ plan list                          # list loaded plans
writ plan set gospels                   # set active plan
writ plan status                        # show progress
writ continue                           # read next entry
writ done                               # mark done, advance
```

**Plan file format:**

```
# Self-paced (no dates)
ge 1
ge 2
mt 1-2

# Calendar-dated
2026-01-01 ge 1-2
2026-01-01 mt 1
2026-01-02 ge 3-4
```

Bundled plans in `data/plans/`:
- `gospels.txt` — Matthew → John
- `new-testament.txt` — full NT, canonical order
- `psalms-and-proverbs.txt` — interleaved wisdom literature

If you're behind on a dated plan, `writ continue` prompts you to catch up, reset to today, or keep reading from where you left off.

### Bookmarks

```bash
writ bookmark add devotionals/morning   # bookmark last verse
writ bookmark add path ge 1 1           # bookmark specific verse
writ bm list                            # tree view of all bookmarks
writ bm list devotionals/               # browse a subtree
writ bm go 3                            # jump to bookmark #3
writ bm remove 3
```

### Notes (margin annotations)

```bash
writ note add "God's sovereignty in creation"   # annotate last verse
writ note add "key verse" ge 1 1                # annotate specific verse
writ note list                                  # all notes
writ note list ge                               # notes in Genesis
writ note list ge 1                             # notes in Genesis 1
writ note remove ge 1 1
```

Notes are translation-agnostic and appear inline when reading.

### Search

```bash
writ search "love your neighbor"
writ search "faith" -t kjv
writ search "fear not" -b is          # search within Isaiah only
```

### Other commands

```bash
writ daily                            # verse of the day (deterministic, offline)
writ random                           # random verse
writ random ps                        # random verse from Psalms
writ compare ge 1 1 web,kjv           # side-by-side translation comparison
writ history                          # recent reading history + streak
writ translations                     # list installed translations
writ books                            # all 66 books + abbreviations
writ set translation web              # set default translation
writ setup                            # re-download / reinstall WEB translation
```

---

## Data storage

All user data lives at `~/.local/share/writ/` (override with `$WRIT_DATA`):

```
~/.local/share/writ/
├── writ.db                  # bookmarks, notes, plans, history, settings
└── translations/
    ├── web.db
    └── ...
```

---

## Uninstall

```bash
rm -rf ~/.local/share/writ
rm ~/.local/bin/writ
```

---

## Contributing

Issues and PRs welcome at [github.com/Spasm0dic/WRIT](https://github.com/Spasm0dic/WRIT).  
See `scripts/import_translation.py` to add new input format support.
