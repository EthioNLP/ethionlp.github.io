"""Writing a news item.

Every route into the news section ends here: the issue form, the shared web
form, the Telegram bot and the event scanner. A submission therefore looks the
same however it arrived, and there is one place to change the format.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .common import ROOT, slugify

NEWS_DIR = ROOT / "_news"

# The vocabulary the site filters on. Anything unrecognised becomes "update",
# which is deliberately bland: a wrong category is worse than a vague one.
KINDS = {
    "conference or workshop": "conference",
    "conference": "conference",
    "workshop": "conference",
    "talk or tutorial": "talk",
    "talk": "talk",
    "tutorial": "talk",
    "award or recognition": "award",
    "award": "award",
    "release (dataset, model, tool)": "release",
    "release": "release",
    "press or media": "press",
    "press": "press",
    "media": "press",
    "other": "update",
}


def parse_date(raw: str | None) -> dt.date:
    """Accept the formats people actually type. Falls back to today."""
    text = (raw or "").strip()
    if not text:
        return dt.date.today()

    for fmt in ("%Y-%m-%d", "%Y-%m", "%d/%m/%Y", "%d.%m.%Y", "%d %B %Y",
                "%B %d, %Y", "%B %Y", "%d %b %Y", "%b %d, %Y"):
        try:
            parsed = dt.datetime.strptime(text, fmt).date()
            return parsed.replace(day=1) if fmt in ("%Y-%m", "%B %Y") else parsed
        except ValueError:
            continue

    # Last resort: a bare year, or a date embedded in a longer string.
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        y, m, d = (int(g) for g in match.groups())
        try:
            return dt.date(y, m, d)
        except ValueError:
            pass
    match = re.search(r"\b(20\d{2})\b", text)
    if match:
        return dt.date(int(match.group(1)), 1, 1)
    return dt.date.today()


def yaml_str(value: str) -> str:
    """Quote a scalar when YAML would otherwise misread it."""
    text = " ".join((value or "").split())
    if not text:
        return '""'
    if text[0] in "-?:,[]{}#&*!|>'\"%@`" or ": " in text or text.endswith(":"):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def unique_path(date: dt.date, title: str) -> Path:
    """A dated filename, suffixed if that name is already taken."""
    base = f"{date.isoformat()}-{slugify(title)[:60]}"
    path = NEWS_DIR / f"{base}.md"
    n = 2
    while path.exists():
        path = NEWS_DIR / f"{base}-{n}.md"
        n += 1
    return path


def write_news(
    *,
    title: str,
    body: str,
    date: str | None = None,
    kind: str | None = None,
    link: str | None = None,
    people: str | None = None,
    source: str | None = None,
    submitter: str | None = None,
    published: bool = False,
) -> Path:
    """Write one news item and return its path.

    `published` defaults to False for anything arriving automatically: an item
    submitted by a stranger, or drafted by a script, should be read by a
    maintainer before it appears. Jekyll drops `published: false` documents from
    the build entirely, so the check is enforced by the file rather than by
    anyone remembering to look.
    """
    if not title or not title.strip():
        raise ValueError("a news item needs a title")

    when = parse_date(date)
    NEWS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        f"title: {yaml_str(title)}",
        f"date: {when.isoformat()}",
        f"kind: {KINDS.get((kind or '').strip().lower(), 'update')}",
    ]
    if link and link.strip():
        lines.append(f"link: {link.strip()}")
    if people and people.strip():
        # Kept as free text: a name here may or may not match a member file, and
        # guessing wrong is worse than not linking.
        lines.append(f"people: {yaml_str(people)}")
    if source:
        lines.append(f"source: {source}")
    if submitter:
        lines.append(f"submitted_by: {yaml_str(submitter)}")

    if not published:
        lines += [
            "",
            "# Submitted, not yet published. Jekyll skips `published: false`, so",
            "# this is invisible on the site until someone has read it, tidied",
            "# the wording and deleted the line below.",
            "published: false",
        ]

    lines += ["---", ""]

    text = " ".join((body or "").split())
    lines.append(text if text else "_No description was given._")
    lines.append("")

    path = unique_path(when, title)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
