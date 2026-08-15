#!/usr/bin/env python3
"""
Scan project directories for new issues and rebuild gallery HTML.

Naming conventions
------------------
Scotch Broom (scotch-broom/):
  SBPoster-{MMM}{YY}[-v{N}].{jpg|png}
  ScotchBroom-{MMM}{YY}.pdf          (optional download)

  Examples:
    scotch-broom/SBPoster-AUG26.jpg
    scotch-broom/SBPoster-AUG26-v2.png
    scotch-broom/ScotchBroom-AUG26.pdf

  MMM = JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
  YY  = two-digit year
  When multiple versions share a month, the highest -vN wins.

POETICS zines (poetics-zine/) — bimonthly:
  POETICS-Zine-{MM}{YY}.{jpg|pdf}

  Examples:
    poetics-zine/POETICS-Zine-0726.jpg   # July/August 2026 (Issue 01)
    poetics-zine/POETICS-Zine-0926.pdf   # September/October 2026 (Issue 02)

  MM = first month of the pair (01, 03, 05, 07, 09, 11)
  YY = two-digit year
  Display label is "{Start}/{End} {Year}", e.g. July/August 2026.

Optional metadata (artist, title, issue label) lives in:
  data/scotch-broom.meta.json   keys: MMMYY (e.g. "AUG26")
  data/poetics.meta.json        keys: MMYY  (e.g. "0726")

HTML markers replaced by this script:
  index.html
    <!-- LATEST:SCOTCH-BROOM:START --> … <!-- LATEST:SCOTCH-BROOM:END -->
    <!-- LATEST:POETICS:START --> … <!-- LATEST:POETICS:END -->
  scotch-broom/index.html
    <!-- GALLERY:SCOTCH-BROOM:START --> … <!-- GALLERY:SCOTCH-BROOM:END -->
  poetics-zine/index.html
    <!-- GALLERY:POETICS:START --> … <!-- GALLERY:POETICS:END -->
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SB_DIR = "scotch-broom"
POETICS_DIR = "poetics-zine"

MONTH_ABBR = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# SBPoster-AUG26.jpg | SBPoster-AUG26-v2.png
SB_IMAGE_RE = re.compile(
    r"^SBPoster-(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
    r"(?P<yy>\d{2})(?:-v(?P<ver>\d+))?\.(?P<ext>jpe?g|png)$",
    re.IGNORECASE,
)
# ScotchBroom-AUG26.pdf
SB_PDF_RE = re.compile(
    r"^ScotchBroom-(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
    r"(?P<yy>\d{2})\.pdf$",
    re.IGNORECASE,
)
# Odd months are the first month of each bimonthly pair.
POETICS_PERIOD_MONTHS = 2
POETICS_START_MONTHS = (1, 3, 5, 7, 9, 11)

# POETICS-Zine-0726.jpg | POETICS-Zine-0926.pdf
POETICS_RE = re.compile(
    r"^POETICS-Zine-(?P<mm>\d{2})(?P<yy>\d{2})\.(?P<ext>jpe?g|png|pdf)$",
    re.IGNORECASE,
)


@dataclass
class Issue:
    """A single published issue (one month / one zine)."""
    key: str  # e.g. AUG26 or 0726
    year: int
    month: int
    version: int = 0
    # Number of calendar months this issue covers (1 = monthly, 2 = bimonthly).
    period_months: int = 1
    # Filenames only (assets live in the project directory)
    thumb: str | None = None
    fullsize: str | None = None
    pdf: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def sort_key(self) -> tuple[int, int, int]:
        return (self.year, self.month, self.version)

    @property
    def month_label(self) -> str:
        """Caption date: 'August 2026' or 'July/August 2026' for bimonthly zines."""
        if self.meta.get("period"):
            return str(self.meta["period"])

        start_name = MONTH_NAMES[self.month]
        if self.period_months <= 1:
            return f"{start_name} {self.year}"

        end_month = self.month + self.period_months - 1
        end_year = self.year
        if end_month > 12:
            end_month -= 12
            end_year += 1
        end_name = MONTH_NAMES[end_month]
        if end_year == self.year:
            return f"{start_name}/{end_name} {self.year}"
        return f"{start_name} {self.year}/{end_name} {end_year}"

    @property
    def display_label(self) -> str:
        """Subtitle under the month (artist or issue number)."""
        if self.meta.get("label"):
            return str(self.meta["label"])
        if self.meta.get("artist"):
            return str(self.meta["artist"])
        if self.meta.get("issue") is not None:
            return f"Issue {int(self.meta['issue']):02d}"
        return ""

    def href(self) -> str | None:
        """Best link target: full-size image preferred, then PDF, then thumb."""
        return self.fullsize or self.pdf or self.thumb

    def img_src(self) -> str | None:
        return self.thumb or self.fullsize


def load_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}


def year_from_yy(yy: str) -> int:
    """Map two-digit year to four-digit (00–69 → 2000s, 70–99 → 1900s)."""
    n = int(yy)
    return 2000 + n if n < 70 else 1900 + n


def discover_scotch_broom(project_dir: Path, meta: dict) -> list[Issue]:
    if not project_dir.is_dir():
        return []

    by_key: dict[str, Issue] = {}

    for path in sorted(project_dir.iterdir()):
        if not path.is_file() or path.name == "index.html":
            continue
        name = path.name

        m = SB_IMAGE_RE.match(name)
        if m:
            mon = m.group("mon").upper()
            yy = m.group("yy")
            ver = int(m.group("ver") or 0)
            ext = m.group("ext").lower()
            if ext == "jpeg":
                ext = "jpg"
            key = f"{mon}{yy}"
            year = year_from_yy(yy)
            month = MONTH_ABBR[mon]

            issue = by_key.get(key)
            if issue is None or ver > issue.version:
                # New issue or higher version: start fresh for image fields
                # but keep PDF if already found for this key.
                existing_pdf = issue.pdf if issue else None
                issue = Issue(
                    key=key,
                    year=year,
                    month=month,
                    version=ver,
                    pdf=existing_pdf,
                    meta=meta.get(key, {}),
                )
                by_key[key] = issue
            elif ver < issue.version:
                continue  # older version; ignore

            if ext == "jpg":
                issue.thumb = name
            elif ext == "png":
                # Prefer PNG as full-size; use as thumb only if no jpg yet
                issue.fullsize = name
                if not issue.thumb:
                    issue.thumb = name
            continue

        m = SB_PDF_RE.match(name)
        if m:
            mon = m.group("mon").upper()
            yy = m.group("yy")
            key = f"{mon}{yy}"
            year = year_from_yy(yy)
            month = MONTH_ABBR[mon]
            if key not in by_key:
                by_key[key] = Issue(
                    key=key,
                    year=year,
                    month=month,
                    meta=meta.get(key, {}),
                )
            by_key[key].pdf = name

    issues = [i for i in by_key.values() if i.img_src() or i.pdf]
    issues.sort(key=lambda i: i.sort_key, reverse=True)
    return issues


def discover_poetics(project_dir: Path, meta: dict) -> list[Issue]:
    if not project_dir.is_dir():
        return []

    by_key: dict[str, Issue] = {}

    for path in sorted(project_dir.iterdir()):
        if not path.is_file() or path.name == "index.html":
            continue
        m = POETICS_RE.match(path.name)
        if not m:
            continue

        mm = m.group("mm")
        yy = m.group("yy")
        ext = m.group("ext").lower()
        if ext == "jpeg":
            ext = "jpg"
        month = int(mm)
        if month < 1 or month > 12:
            print(f"warning: skipping {path.name} (invalid month {mm})", file=sys.stderr)
            continue
        if month not in POETICS_START_MONTHS:
            print(
                f"warning: {path.name} uses month {mm}; POETICS issues are bimonthly. "
                "Use the first month of the pair (01, 03, 05, 07, 09, 11). "
                f"This file will display as a pair starting in {MONTH_NAMES[month]}.",
                file=sys.stderr,
            )

        key = f"{mm}{yy}"
        year = year_from_yy(yy)
        name = path.name

        if key not in by_key:
            by_key[key] = Issue(
                key=key,
                year=year,
                month=month,
                period_months=POETICS_PERIOD_MONTHS,
                meta=meta.get(key, {}),
            )
        issue = by_key[key]

        if ext in ("jpg", "png"):
            if ext == "jpg" or not issue.thumb:
                issue.thumb = name
            if ext == "png":
                issue.fullsize = name
        elif ext == "pdf":
            issue.pdf = name

    issues = [i for i in by_key.values() if i.img_src() or i.pdf]
    issues.sort(key=lambda i: i.sort_key, reverse=True)
    return issues


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def asset_url(filename: str | None, path_prefix: str) -> str:
    """Build a URL for an asset filename with an optional directory prefix."""
    if not filename:
        return ""
    return f"{path_prefix}{filename}"


def render_card(
    issue: Issue,
    *,
    frame_class: str,
    action: str,
    path_prefix: str,
    width: int,
    height: int,
    default_alt: str,
) -> str:
    href = issue.href()
    img = issue.img_src()
    if not href or not img:
        return ""

    href = asset_url(href, path_prefix)
    img = asset_url(img, path_prefix)

    title = issue.meta.get("title")
    artist = issue.meta.get("artist")
    month = issue.month_label
    label = issue.display_label

    if title and artist:
        alt = f"{default_alt}: {title} by {artist}, {month}"
    elif title:
        alt = f"{default_alt}: {title}, {month}"
    else:
        alt = f"{default_alt}, {month}"

    label_html = ""
    if label:
        label_html = f'\n                  <span class="artist">{escape_html(label)}</span>'

    return f"""            <article class="item-card">
              <a class="item-link" href="{escape_html(href)}" target="_blank" rel="noopener noreferrer">
                <div class="item-frame {frame_class}">
                  <img
                    src="{escape_html(img)}"
                    alt="{escape_html(alt)}"
                    width="{width}"
                    height="{height}"
                    loading="lazy"
                  >
                </div>
                <div class="item-caption">
                  <span class="month">{escape_html(month)}</span>{label_html}
                  <span class="action">{escape_html(action)}</span>
                </div>
              </a>
            </article>"""


def render_grid(
    issues: list[Issue],
    *,
    gallery: bool,
    frame_class: str,
    action: str,
    path_prefix: str,
    width: int,
    height: int,
    default_alt: str,
) -> str:
    if not issues:
        empty = (
            '          <p class="section-head" style="margin:0">'
            "No issues yet — check back soon.</p>"
        )
        return empty

    grid_class = "item-grid item-grid--gallery" if gallery else "item-grid"
    cards = [
        render_card(
            issue,
            frame_class=frame_class,
            action=action,
            path_prefix=path_prefix,
            width=width,
            height=height,
            default_alt=default_alt,
        )
        for issue in issues
    ]
    cards = [c for c in cards if c]
    body = "\n".join(cards)
    return f'          <div class="{grid_class}">\n{body}\n          </div>'


def replace_marker(html: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf"(<!--\s*{re.escape(name)}:START\s*-->)(.*?)(<!--\s*{re.escape(name)}:END\s*-->)",
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        raise SystemExit(f"error: marker {name} not found in HTML")
    # Preserve the indentation of the START comment for the END comment
    line_start = html.rfind("\n", 0, match.start()) + 1
    indent = html[line_start:match.start()]
    replacement = f"{match.group(1)}\n{content}\n{indent}{match.group(3)}"
    return html[: match.start()] + replacement + html[match.end() :]


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    sb_meta = load_meta(ROOT / "data" / "scotch-broom.meta.json")
    poetics_meta = load_meta(ROOT / "data" / "poetics.meta.json")

    sb_issues = discover_scotch_broom(ROOT / SB_DIR, sb_meta)
    poetics_issues = discover_poetics(ROOT / POETICS_DIR, poetics_meta)

    print(f"Scotch Broom: {len(sb_issues)} issue(s)")
    for i in sb_issues:
        print(f"  - {i.key} v{i.version}  thumb={i.thumb}  full={i.fullsize}  pdf={i.pdf}")
    print(f"POETICS: {len(poetics_issues)} issue(s)")
    for i in poetics_issues:
        print(f"  - {i.key}  thumb={i.thumb}  pdf={i.pdf}")

    sb_latest = sb_issues[:1]
    poetics_latest = poetics_issues[:1]

    # —— index.html (paths relative to site root) ——
    index_path = ROOT / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    index_html = replace_marker(
        index_html,
        "LATEST:SCOTCH-BROOM",
        render_grid(
            sb_latest,
            gallery=False,
            frame_class="item-frame--broadside",
            action="View full size →",
            path_prefix=f"{SB_DIR}/",
            width=612,
            height=1008,
            default_alt="Poetry broadside",
        ),
    )
    index_html = replace_marker(
        index_html,
        "LATEST:POETICS",
        render_grid(
            poetics_latest,
            gallery=False,
            frame_class="item-frame--zine",
            action="Read PDF →",
            path_prefix=f"{POETICS_DIR}/",
            width=396,
            height=612,
            default_alt="POETICS zine cover",
        ),
    )
    changed = []
    if write_if_changed(index_path, index_html):
        changed.append("index.html")

    # —— scotch-broom/index.html (assets in same directory) ——
    sb_page = ROOT / SB_DIR / "index.html"
    sb_html = sb_page.read_text(encoding="utf-8")
    sb_html = replace_marker(
        sb_html,
        "GALLERY:SCOTCH-BROOM",
        render_grid(
            sb_issues,
            gallery=True,
            frame_class="item-frame--broadside",
            action="View full size →",
            path_prefix="",
            width=612,
            height=1008,
            default_alt="Poetry broadside",
        ),
    )
    if write_if_changed(sb_page, sb_html):
        changed.append(f"{SB_DIR}/index.html")

    # —— poetics-zine/index.html (assets in same directory) ——
    pz_page = ROOT / POETICS_DIR / "index.html"
    pz_html = pz_page.read_text(encoding="utf-8")
    pz_html = replace_marker(
        pz_html,
        "GALLERY:POETICS",
        render_grid(
            poetics_issues,
            gallery=True,
            frame_class="item-frame--zine",
            action="Read PDF →",
            path_prefix="",
            width=396,
            height=612,
            default_alt="POETICS zine cover",
        ),
    )
    if write_if_changed(pz_page, pz_html):
        changed.append(f"{POETICS_DIR}/index.html")

    if changed:
        print("Updated:", ", ".join(changed))
    else:
        print("No HTML changes needed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
