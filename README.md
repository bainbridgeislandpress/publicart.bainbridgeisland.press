# public.bainbridgeisland.press

Public art site for [Bainbridge Island Press](https://bainbridgeisland.press): **Scotch Broom** poetry broadsides and **POETICS** zines.

## Site structure

| Path | Purpose |
|------|---------|
| `/` | Home — latest Scotch Broom broadside + latest POETICS zine |
| `/scotch-broom/` | Project page + full broadside gallery (assets live here) |
| `/poetics-zine/` | Project page + full zine gallery (assets live here) |

Each project directory holds its own `index.html` plus the poster/zine source files.

## Adding a new issue

Drop files into the right project folder with the naming convention below, optionally add metadata, then either:

```bash
python3 scripts/build_galleries.py
```

…or push to `main` and the **Update galleries** GitHub Action will rebuild the HTML automatically.

### Scotch Broom (`scotch-broom/`)

| File | Role |
|------|------|
| `ScotchBroom-{MM}{YY}.jpg` | Gallery thumbnail (recommended) |
| `ScotchBroom-{MM}{YY}.png` | Full-size image (linked from the card) |
| `ScotchBroom-{MM}{YY}-v{N}.jpg` / `.png` | Versioned revision (highest `vN` wins) |
| `ScotchBroom-{MM}{YY}.pdf` | Optional PDF download |

**Month (`MM`):** two digits, `01`–`12`  
**Year (`YY`):** two digits (`26` → 2026)

An issue needs a `.jpg` or `.png` to appear in the gallery; a PDF on its own is skipped with a warning.

Examples:

```
scotch-broom/ScotchBroom-0926.jpg   # September 2026
scotch-broom/ScotchBroom-0926.png
scotch-broom/ScotchBroom-0926.pdf
```

Optional metadata in `data/scotch-broom.meta.json` (key = `MMYY`):

```json
{
  "0926": {
    "artist": "Poet Name",
    "title": "Poem Title",
    "label": "Poet Name"
  }
}
```

- `label` — subtitle under the month (defaults to `artist` if omitted)
- `title` / `artist` — used in image `alt` text

### POETICS zines (`poetics-zine/`)

POETICS is published **every two months**. Issue 01 is **July/August 2026**; later issues follow the same window (September/October, November/December, January/February, …).

| File | Role |
|------|------|
| `POETICS-Zine-{MM}{YY}.jpg` | Cover image |
| `POETICS-Zine-{MM}{YY}.pdf` | Downloadable issue (linked from the card) |

**Month (`MM`):** first month of the pair — `01` `03` `05` `07` `09` `11`  
**Year:** two digits (`26` → 2026)

The gallery caption is the two-month window, e.g. `0726` → **July/August 2026**.

| Issue window | Filename |
|--------------|----------|
| January/February | `POETICS-Zine-01YY` |
| March/April | `POETICS-Zine-03YY` |
| May/June | `POETICS-Zine-05YY` |
| July/August | `POETICS-Zine-07YY` |
| September/October | `POETICS-Zine-09YY` |
| November/December | `POETICS-Zine-11YY` |

Examples:

```
poetics-zine/POETICS-Zine-0726.jpg   # Issue 01 — July/August 2026
poetics-zine/POETICS-Zine-0726.pdf
poetics-zine/POETICS-Zine-0926.jpg   # Issue 02 — September/October 2026
poetics-zine/POETICS-Zine-0926.pdf
```

Optional metadata in `data/poetics.meta.json` (key = `MMYY`, first month of the pair):

```json
{
  "0926": {
    "label": "Issue 02",
    "issue": 2,
    "title": "POETICS Zine"
  }
}
```

- `label` — subtitle under the period (defaults to `Issue NN` if `issue` is set)
- `title` — used in image `alt` text
- `period` — optional caption override (otherwise derived from the filename month)

## Build script

`scripts/build_galleries.py` scans `scotch-broom/` and `poetics-zine/`, merges optional metadata, and rewrites only the marked regions in:

- `index.html` — latest issue of each project  
- `scotch-broom/index.html` — full Scotch Broom gallery  
- `poetics-zine/index.html` — full POETICS gallery  

Markers look like:

```html
<!-- LATEST:SCOTCH-BROOM:START -->
…
<!-- LATEST:SCOTCH-BROOM:END -->
```

Hand-edit project descriptions and shared layout freely; keep those comment markers in place so the script can update galleries.

## GitHub Action

`.github/workflows/update-galleries.yml` runs on pushes to `main` that touch `scotch-broom/`, `poetics-zine/`, `data/`, or the build script. It runs the script and commits any HTML changes.

POETICS filenames use the first month of each two-month window (`0726` = July/August 2026). The Action’s build script turns that into the gallery caption, so a new `POETICS-Zine-0926` pair will show as **September/October 2026**.
