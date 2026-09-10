#!/usr/bin/env python3
"""Look for community participation in watched events, and draft news items.

Run weekly by .github/workflows/scan-events.yml, which opens a pull request with
whatever it finds. Nothing this script writes is ever published automatically, every draft carries ``published: false``, so Jekyll leaves it out of the site
until a human removes that line. That is the admin verification step, and it is
enforced by the file rather than by anyone remembering to check.

Two kinds of evidence, both used:

* a public programme, schedule or accepted-papers page that names someone
  listed on this site;
* a synced publication whose venue matches the event and whose year matches the
  edition, a paper at a venue is strong evidence of taking part.

When several people or teams turn up at the same event; they are aggregated into
ONE draft, because "eleven of us were at the Indaba" is the news, not eleven
separate notes.

    python3 scripts/scan_events.py                 # write drafts
    python3 scripts/scan_events.py --dry-run       # report only
    python3 scripts/scan_events.py --year 2025

On LinkedIn
───────────
LinkedIn itself is never fetched, its robots.txt disallows every bot it has not
whitelisted, and says so in words as well. What this script can do instead is
query a *search engine's* index of the LinkedIn pages LinkedIn allowed it to
publish, which is the one form of automated access LinkedIn's own robots.txt
sanctions. That needs BRAVE_SEARCH_API_KEY in the environment and is skipped
without it. See `search_linkedin` for the detail, and expect thin results: group
posts are not indexed at all.

Anything a search engine has not indexed should be submitted through the "Share
community news" issue form.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import urllib.parse
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    DATA,
    GENERATED,
    ROOT,
    get_json,
    get_text,
    info,
    read_members,
    step,
    warn,
)

NEWS_DIR = ROOT / "_news"

# A name must appear as a whole phrase. Substring matching on names as short and
# as widely shared as these would report half of Ethiopia as having attended.
MIN_NAME_WORDS = 2


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalise(text: str) -> str:
    """Lowercase, unaccented, single-spaced, for comparing names to page text."""
    text = strip_accents(text or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()


def name_variants(member: dict) -> list[str]:
    """The forms a person's name plausibly takes in a programme listing."""
    names = [member.get("name") or ""] + list(member.get("aliases") or [])
    out = []
    for name in names:
        parts = normalise(name).split()
        if len(parts) < MIN_NAME_WORDS:
            continue
        out.append(" ".join(parts))
        # "Seid Yimam" for "Seid Muhie Yimam", first and last only.
        if len(parts) > 2:
            out.append(f"{parts[0]} {parts[-1]}")
    return list(dict.fromkeys(out))


def load_generated(name: str) -> dict:
    path = GENERATED / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ─── LinkedIn, via a search engine index ──────────────────────────────────────
#
# LinkedIn cannot be crawled by us. Its robots.txt answers `User-agent: *` with
# `Disallow: /`, a blanket refusal to every bot it has not whitelisted, and the
# file opens with "The use of robots or other automated means to access LinkedIn
# without the express permission of LinkedIn is strictly prohibited". Our own
# group's path, /groups/, is disallowed even for Googlebot.
#
# The one form of access LinkedIn does sanction is stated in that same file:
# crawling "for the limited purpose of including content in approved publicly
# available search engines". So this queries a search engine's index rather than
# LinkedIn itself. We read what LinkedIn permitted a search engine to publish,
# which is a different act from scraping LinkedIn, and it is the only route that
# does not require ignoring an explicit refusal.
#
# It needs a search API key in the environment, and is skipped without one:
#
#     BRAVE_SEARCH_API_KEY=...   (free tier, https://brave.com/search/api/)
#
# Expect thin results. Group posts are not indexed at all, and member posts are
# indexed inconsistently, so this supplements the programme and publication
# scans rather than replacing them.

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def search_linkedin(event: dict, year: int, members: list[dict]) -> list[dict]:
    """Public LinkedIn pages a search engine has indexed for this event."""
    key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not key:
        return []

    query = f'site:linkedin.com "{event["name"]}" {year} (EthioNLP OR Ethiopia OR Amharic)'
    url = f"{BRAVE_ENDPOINT}?q={urllib.parse.quote(query)}&count=20"

    data = get_json(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": key,
    })
    if not data:
        warn("search API returned nothing, check BRAVE_SEARCH_API_KEY")
        return []

    variants = {}
    for member in members:
        for v in name_variants(member):
            variants[v] = member["slug"]

    hits = []
    for result in (data.get("web") or {}).get("results") or []:
        blob = normalise(f"{result.get('title', '')} {result.get('description', '')}")
        named = sorted({slug for v, slug in variants.items() if v in blob})
        if not named:
            continue
        hits.append({
            "url": result.get("url"),
            "title": (result.get("title") or "").strip(),
            "members": named,
        })
    return hits


def scan_pages(event: dict, members: list[dict]) -> dict[str, list[str]]:
    """Members named on the event's public pages. Returns slug → [source urls]."""
    hits: dict[str, list[str]] = {}
    for url in event.get("pages") or []:
        raw = get_text(url)
        if not raw:
            warn(f"could not read {url}")
            continue
        try:
            text = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
        except Exception:  # noqa: BLE001 - a page we cannot decode is just a miss
            continue

        # Strip tags so a name split across markup still matches.
        blob = normalise(re.sub(r"<[^>]+>", " ", text))
        for member in members:
            for variant in name_variants(member):
                if variant in blob:
                    hits.setdefault(member["slug"], [])
                    if url not in hits[member["slug"]]:
                        hits[member["slug"]].append(url)
                    break
    return hits


def scan_publications(event: dict, year: int, members: list[dict]) -> dict[str, list[dict]]:
    """Members with a paper at this event in this year. Returns slug → [papers]."""
    matches = [m.lower() for m in event.get("venue_match") or []]
    if not matches:
        return {}

    pubs = load_generated("publications.yml").get("publications") or []
    by_slug: dict[str, list[dict]] = {}
    for pub in pubs:
        if pub.get("year") != year:
            continue
        venue = (pub.get("venue") or "").lower()
        if not any(m in venue for m in matches):
            continue
        for slug in pub.get("members") or []:
            by_slug.setdefault(slug, []).append(pub)
    return by_slug


def sentence(names: list[str]) -> str:
    """Join names the way a person would write them."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def draft(event: dict, year: int, people: dict, papers: dict, members_by_slug: dict) -> str:
    slugs = sorted(set(people) | set(papers))
    names = [members_by_slug[s]["name"] for s in slugs if s in members_by_slug]

    month = (event.get("months") or [1])[0]
    date = dt.date(year, month, 1).isoformat()

    lines = [
        "---",
        f"title: EthioNLP at {event['name']} {year}",
        f"date: {date}",
        "kind: conference",
    ]
    if event.get("homepage"):
        lines.append(f"link: {event['homepage']}")
    lines += [
        "",
        "# ── DRAFT, NOT PUBLISHED ────────────────────────────────────────────",
        "# Found automatically by scripts/scan_events.py. Jekyll skips any file",
        "# with `published: false`, so this is invisible on the site until an",
        "# admin has checked it and deleted that line.",
        "#",
        "# Before publishing, please:",
        "#   1. confirm these people actually took part, a name on a page is",
        "#      evidence, not proof, and namesakes exist;",
        "#   2. rewrite the body. What is below is a statement of the finding,",
        "#      not something anyone would want to read;",
        "#   3. add a photograph if there is one, and delete this comment block.",
        "published: false",
        "---",
        "",
    ]

    if names:
        lines.append(f"{sentence(names)} took part in {event['name']} {year}.")
        lines.append("")

    if papers:
        total = len({p["title"] for ps in papers.values() for p in ps})
        lines.append(
            f"{total} paper{'s' if total != 1 else ''} from the community appeared at the venue:"
        )
        lines.append("")
        seen = set()
        for slug, items in sorted(papers.items()):
            for paper in items:
                title = paper.get("title") or "Untitled"
                if title in seen:
                    continue
                seen.add(title)
                url = paper.get("url") or paper.get("anthology") or paper.get("doi") or ""
                lines.append(f"- [{title}]({url})" if url else f"- {title}")
        lines.append("")

    if people:
        lines.append("<!-- Named on:")
        for slug, urls in sorted(people.items()):
            who = members_by_slug.get(slug, {}).get("name", slug)
            lines.append(f"     {who}: {', '.join(urls)}")
        lines.append("-->")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report only")
    parser.add_argument("--year", type=int, default=dt.date.today().year)
    args = parser.parse_args()

    path = DATA / "watched_events.yml"
    if not path.exists():
        warn("no _data/watched_events.yml, nothing to scan")
        return 0
    with path.open(encoding="utf-8") as fh:
        events = yaml.safe_load(fh) or []

    members = read_members()
    by_slug = {m["slug"]: m for m in members}

    written = 0
    for event in events:
        step(f"{event['name']} {args.year}")

        people = scan_pages(event, members)
        papers = scan_publications(event, args.year, members)
        posts = search_linkedin(event, args.year, members)

        for post in posts:
            for slug in post["members"]:
                people.setdefault(slug, [])
                if post["url"] not in people[slug]:
                    people[slug].append(post["url"])
        if posts:
            info(f"{len(posts)} indexed LinkedIn page(s) naming a member")

        if not people and not papers:
            info("nothing found")
            continue

        found = sorted(set(people) | set(papers))
        info(f"{len(found)} member(s): " + ", ".join(by_slug[s]["name"] for s in found if s in by_slug))
        if papers:
            info(f"{sum(len(v) for v in papers.values())} paper credits at the venue")

        target = NEWS_DIR / f"{args.year}-{(event.get('months') or [1])[0]:02d}-01-{event['slug']}-{args.year}.md"
        if target.exists():
            info(f"{target.name} already exists, leaving it alone")
            continue

        if args.dry_run:
            info(f"would write {target.name}")
            continue

        target.write_text(draft(event, args.year, people, papers, by_slug), encoding="utf-8")
        info(f"wrote {target.relative_to(ROOT)}")
        written += 1

    step("Summary")
    info(f"{written} draft(s) written" if written else "no new drafts")
    if written:
        info("each carries `published: false`, an admin must remove that line")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
