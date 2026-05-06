# vrs

Lightning-fast terminal Bible reference and reading tool.  
Built for speed, offline-first, cyberdeck-friendly.

```
vrs ge 1 1-3          # Genesis 1:1-3 (default translation)
vrs jn 3 16 -t kjv    # John 3:16 in KJV
vrs ps 23             # Psalm 23, interactive chapter navigation
vrs daily             # verse of the day
vrs continue          # resume active reading plan
```

---

## Install

```bash
pip install .
```

Requires Python 3.10+.  Dependencies: `typer`, `rich`.

---

## Getting a Translation

vrs ships with no translation text — Bible translations have complex licensing.  
The **World English Bible (WEB)** is fully public domain and a great default.

**Quick start with WEB:**

1. Download the CSV from [eBible.org](https://ebible.org) or the
   [openbible.info labs bulk download](https://openbible.info/labs/parse/).  
   The expected columns are: `b, c, v, t`  (book number, chapter, verse, text).

2. Import it:
   ```bash
   python scripts/import_translation.py web.csv -n web --format csv
   ```

3. Set it as default:
   ```bash
   vrs set translation web
   ```

**Other formats supported by the importer:**

| Format | Flag | Description |
|--------|------|-------------|
| CSV    | `--format csv` | `book,chapter,verse,text` |
| TSV    | `--format tsv` | `book\tchapter\tverse\ttext` |
| VPL    | `--format vpl` | `GEN 1:1 In the beginning...` |

---

## Commands

### Lookup (default)

```
vrs <book> [chapter] [verses] [-t translation] [-c compare]

vrs ge                   # Genesis ch.1, interactive nav
vrs ge 1                 # Genesis 1, interactive nav
vrs ge 1 1               # Genesis 1:1
vrs ge 1 1-3             # Genesis 1:1-3
vrs ro 8 28,35           # Romans 8:28 and 8:35
vrs ge 1 1 -t esv        # with specific translation
vrs ge 1 1 -c kjv        # display side by side with KJV
```

After displaying a verse, a quick-action bar appears:  
`[b]ookmark  [+]note  [q]uit`

During chapter reading, the nav bar shows:  
`[p]rev  [n]ext  [b]ookmark  [+]note  [q]uit`

### Book abbreviations

All 66 books have short canonical abbreviations. Run `vrs books` to see them all.

Key conflict resolutions:

| Short | Book |
|-------|------|
| `jn`  | John |
| `1jn` `2jn` `3jn` | 1–3 John |
| `1sa` `2sa` | 1–2 Samuel |
| `1ki` `2ki` | 1–2 Kings |
| `1co` `2co` | 1–2 Corinthians |

### Reading plans

```bash
vrs plan load data/plans/gospels.txt   # import a plan
vrs plan list                          # list loaded plans
vrs plan set gospels                   # set active plan
vrs plan status                        # show progress
vrs continue                           # read next entry
vrs done                               # mark done, advance
```

**Plan file format** — two variants:

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

If you're behind on a dated plan, `vrs continue` will ask whether to catch up,
reset to today, or continue from where you left off.

### Bookmarks

```bash
vrs bookmark add devotionals/morning   # bookmark last verse
vrs bookmark add path ge 1 1           # bookmark specific verse
vrs bm list                            # tree view of all bookmarks
vrs bm list devotionals/               # browse subtree
vrs bm go 3                            # jump to bookmark #3
vrs bm remove 3
```

### Notes (margin annotations)

```bash
vrs note add "God's sovereignty in creation"   # annotate last verse
vrs note add "key verse" ge 1 1                # annotate specific verse
vrs note list                                  # all notes
vrs note list ge                               # notes in Genesis
vrs note list ge 1                             # notes in Genesis 1
vrs note remove ge 1 1
```

Notes are translation-agnostic and display inline when reading.

### Search

```bash
vrs search "love your neighbor"
vrs search "faith" -t kjv
vrs search "fear not" -b is          # search within Isaiah only
```

### Other

```bash
vrs daily                            # verse of the day (deterministic, offline)
vrs random                           # random verse
vrs random ps                        # random verse from Psalms
vrs compare ge 1 1 web,kjv,esv       # side-by-side translation comparison
vrs history                          # recent reading history + streak
vrs translations                     # list installed translations
vrs books                            # list all books + abbreviations
vrs set translation web              # set default translation
vrs set plan gospels                 # set active plan
```

---

## Data storage

All user data lives in `~/.local/share/vrs/` (override with `$VRS_DATA`):

```
~/.local/share/vrs/
├── vrs.db                  # bookmarks, notes, plans, history, state
└── translations/
    ├── web.db
    ├── kjv.db
    └── ...
```

---

## Shell completion

```bash
vrs --install-completion bash    # bash
vrs --install-completion zsh     # zsh
```

---

## Contributing

Issues, PRs, and translation format support requests welcome.  
See `scripts/import_translation.py` to add new input formats.
