#!/usr/bin/env python3
"""Fill in missing scholarly identifiers on `_members/*.md` files.

A new member only has to give a name and a couple of profile links. This script
looks up the identifiers the publication sync actually needs, an OpenAlex
author id, and an ORCID when the record carries one, and writes them back into
the member's file.

It is deliberately conservative. A candidate is only accepted when the OpenAlex
display name contains both the member's first and last name *and* the author's
top topics are language-technology topics. Ethiopian names are widely shared,
and a wrong match here would silently attribute someone else's parasitology
papers to a member, which is exactly what a naive name search does.

Anything it is not sure about is reported and left alone for a human.

Usage:
    python3 scripts/resolve_ids.py                 # fill in what is missing
    python3 scripts/resolve_ids.py --check         # report only, change nothing
    python3 scripts/resolve_ids.py --member SLUG
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    CONTACT_EMAIL,
    get_json,
    info,
    norm_name,
    read_members,
    step,
    warn,
)

OPENALEX = "https://api.openalex.org"

# An author's OpenAlex topics must overlap these for a match to be accepted.
TOPIC_HINTS = (
    "natural language", "topic modeling", "speech", "machine translation",
    "computational linguistics", "information retrieval", "text mining",
    "multilingual", "semantic", "language model",
)


def plausible(candidate: dict, member_name: str) -> bool:
    display = norm_name(candidate.get("display_name"))
    parts = norm_name(member_name).split()
    if len(parts) < 2:
        return False
    if parts[0] not in display or parts[-1] not in display:
        return False

    topics = " ".join(
        (t.get("display_name") or "").lower() for t in (candidate.get("topics") or [])
    )
    return any(hint in topics for hint in TOPIC_HINTS)


def find_author(member: dict) -> dict | None:
    query = urllib.parse.quote(member["name"])
    data = get_json(f"{OPENALEX}/authors?search={query}&per-page=8&mailto={CONTACT_EMAIL}")
    if not data:
        return None

    names = [member["name"]] + list(member.get("aliases") or [])
    for candidate in data.get("results", []):
        if any(plausible(candidate, name) for name in names):
            return candidate
    return None


def patch(path: Path, key: str, value: str) -> None:
    """Set a front-matter key, whether it is absent or present-but-empty."""
    text = path.read_text(encoding="utf-8")
    empty = re.compile(rf"^{key}:[^\S\n]*$", re.M)

    if empty.search(text):
        text = empty.sub(f"{key}: {value}", text, count=1)
    elif re.search(rf"^{key}:[^\S\n]*\S", text, re.M):
        return  # already set; never overwrite a human's value
    else:
        # Insert before the closing delimiter of the front matter.
        parts = text.split("---", 2)
        if len(parts) < 3:
            warn(f"{path.name}: unexpected front matter, skipping")
            return
        parts[1] = parts[1].rstrip("\n") + f"\n{key}: {value}\n"
        text = "---".join(parts)

    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report only")
    parser.add_argument("--member", help="single member slug")
    args = parser.parse_args()

    members = read_members()
    if args.member:
        members = [m for m in members if m["slug"] == args.member]
        if not members:
            warn(f"no member with slug {args.member!r}")
            return 1

    resolved = unresolved = already = 0

    step(f"Resolving identifiers for {len(members)} member(s)")
    for member in members:
        if member.get("openalex"):
            already += 1
            continue

        candidate = find_author(member)
        if not candidate:
            unresolved += 1
            info(f"{member['name']:<28} no confident match, add `openalex:` by hand")
            continue

        author_id = (candidate.get("id") or "").rstrip("/").split("/")[-1]
        orcid = (candidate.get("orcid") or "").rstrip("/").split("/")[-1] or None
        works = candidate.get("works_count")

        info(f"{member['name']:<28} {author_id}  ({works} works"
             + (f", ORCID {orcid}" if orcid else "") + ")")
        resolved += 1

        if not args.check:
            patch(member["_path"], "openalex", author_id)
            if orcid and not member.get("orcid"):
                patch(member["_path"], "orcid", orcid)

    step("Summary")
    info(f"{already} already had an id, {resolved} resolved, {unresolved} need a human")
    if unresolved:
        info("for those, open their Google Scholar or ORCID page and paste the id in")
    if args.check and resolved:
        info("run without --check to write these into _members/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
