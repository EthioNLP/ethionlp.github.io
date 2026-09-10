#!/usr/bin/env python3
"""Collect news submitted through the low-friction channels.

The community is global and mostly not on GitHub. A GitHub issue form is fine
for the technical core and useless for everyone else, so news arrives by
whichever door suits the person, and they all end at the same place: a draft
file in `_news/`, a pull request, and a maintainer's eye.

Two sources, both needing no account from the person submitting:

**A shared web form.** Any form tool that can publish its responses as a CSV, Google Forms, and most others, works. Publish the responses sheet to the web as
CSV and put the URL in `NEWS_FORM_CSV`. The submitter needs no login and can do
it from a phone, which is the whole point.

**Telegram.** The community already has a channel, so let people post there. A
bot reads its own messages through `getUpdates`; mention it or use `/news` and
the message becomes a draft. Needs `TELEGRAM_BOT_TOKEN`.

Both are skipped when their variable is unset, so this runs safely with neither
configured.

    python3 scripts/from_submissions.py            # write drafts
    python3 scripts/from_submissions.py --dry-run

Nothing is published. Every draft carries `published: false`.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, get_json, get_text, info, step, warn  # noqa: E402
from lib.news import write_news  # noqa: E402

# Where we remember which submissions have already been turned into drafts, so a
# daily run does not recreate yesterday's. Committed with the drafts.
SEEN_FILE = ROOT / "_data" / "generated" / "news_seen.json"

# Column headings are matched loosely: form tools prepend timestamps, people
# rename fields, and translations happen. Each key lists what to look for.
COLUMNS = {
    "title": ["headline", "title", "what happened in a few words"],
    "body": ["description", "what happened", "details", "summary", "tell us"],
    "link": ["link", "url", "post", "reference"],
    "date": ["date", "when"],
    "kind": ["kind", "type", "category"],
    "people": ["who", "people", "names", "involved"],
    "submitter": ["your name", "submitted by", "name of submitter", "email"],
}

TELEGRAM_API = "https://api.telegram.org/bot{token}"
# Only messages that ask to be news become news. A channel is a conversation,
# and turning every message in it into a draft would be unusable.
TELEGRAM_TRIGGER = re.compile(r"^\s*(?:/news|#news)\b[:\s]*", re.I)


def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except (ValueError, OSError):
        warn(f"{SEEN_FILE.name} unreadable, treating everything as new")
        return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")


def pick(row: dict, key: str) -> str | None:
    """Find a column by fuzzy heading match."""
    wanted = COLUMNS[key]
    for heading, value in row.items():
        low = (heading or "").strip().lower()
        if any(w in low for w in wanted) and (value or "").strip():
            return value.strip()
    return None


def from_form(seen: set[str]) -> list[dict]:
    url = os.environ.get("NEWS_FORM_CSV")
    if not url:
        return []

    step("Shared web form")
    raw = get_text(url)
    if not raw:
        warn("could not read NEWS_FORM_CSV")
        return []

    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    rows = list(csv.DictReader(io.StringIO(text)))
    info(f"{len(rows)} response(s) in the sheet")

    out = []
    for row in rows:
        title = pick(row, "title")
        if not title:
            continue
        # The row itself is the identity: a form response is immutable, and
        # hashing the whole row means an edited response counts as new.
        key = "form:" + re.sub(r"\s+", " ", "|".join(f"{k}={v}" for k, v in sorted(row.items())))[:400]
        if key in seen:
            continue
        out.append({
            "key": key,
            "title": title,
            "body": pick(row, "body") or "",
            "link": pick(row, "link"),
            "date": pick(row, "date"),
            "kind": pick(row, "kind"),
            "people": pick(row, "people"),
            "submitter": pick(row, "submitter"),
            "source": "form",
        })
    info(f"{len(out)} new")
    return out


def from_telegram(seen: set[str]) -> list[dict]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return []

    step("Telegram")
    data = get_json(f"{TELEGRAM_API.format(token=token)}/getUpdates?limit=100")
    if not data or not data.get("ok"):
        warn("Telegram returned nothing, check TELEGRAM_BOT_TOKEN")
        return []

    updates = data.get("result") or []
    info(f"{len(updates)} update(s)")

    out = []
    for update in updates:
        message = (
            update.get("message")
            or update.get("channel_post")
            or update.get("edited_message")
            or {}
        )
        text = (message.get("text") or message.get("caption") or "").strip()
        if not text or not TELEGRAM_TRIGGER.match(text):
            continue

        key = f"telegram:{update.get('update_id')}"
        if key in seen:
            continue

        text = TELEGRAM_TRIGGER.sub("", text, count=1).strip()
        if not text:
            continue

        # First line is the headline, the rest the description; any URL in the
        # message becomes the link.
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        title = lines[0][:120]
        body = " ".join(lines[1:]) if len(lines) > 1 else ""
        urls = re.findall(r"https?://\S+", text)

        sender = message.get("from") or {}
        who = " ".join(
            p for p in (sender.get("first_name"), sender.get("last_name")) if p
        ) or sender.get("username")

        out.append({
            "key": key,
            "title": title,
            "body": body or title,
            "link": urls[0] if urls else None,
            "date": None,
            "kind": None,
            "people": None,
            "submitter": who,
            "source": "telegram",
        })
    info(f"{len(out)} new")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report only")
    args = parser.parse_args()

    if not os.environ.get("NEWS_FORM_CSV") and not os.environ.get("TELEGRAM_BOT_TOKEN"):
        step("Nothing configured")
        info("set NEWS_FORM_CSV and/or TELEGRAM_BOT_TOKEN to collect submissions")
        info("see the News section of README.md")
        return 0

    seen = load_seen()
    submissions = from_form(seen) + from_telegram(seen)

    if not submissions:
        step("Summary")
        info("no new submissions")
        return 0

    step(f"{len(submissions)} new submission(s)")
    written = 0
    for item in submissions:
        info(f"{item['source']:<9} {item['title'][:64]}")
        if args.dry_run:
            continue
        try:
            path = write_news(
                title=item["title"], body=item["body"], date=item["date"],
                kind=item["kind"], link=item["link"], people=item["people"],
                source=item["source"], submitter=item["submitter"],
            )
        except ValueError as exc:
            warn(f"skipped: {exc}")
            continue
        info(f"  → {path.relative_to(ROOT)}")
        seen.add(item["key"])
        written += 1

    if not args.dry_run:
        save_seen(seen)

    step("Summary")
    info(f"{written} draft(s) written" if written else "--dry-run: nothing written")
    if written:
        info("each carries `published: false`, a maintainer must read it first")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
