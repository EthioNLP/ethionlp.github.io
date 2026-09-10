#!/usr/bin/env python3
"""Scaffold a `_members/<slug>.md` file from one or more profile URLs.

This is the thing that makes joining cheap: hand it a GitHub, Hugging Face,
ORCID, Google Scholar, DBLP or personal-site URL and it works out the rest,
writes the member file, and leaves you a one-file diff to review.

    python3 scripts/new_member.py https://github.com/someone
    python3 scripts/new_member.py https://huggingface.co/someone https://orcid.org/0000-...
    python3 scripts/new_member.py --name "Full Name" --focus data,models https://github.com/someone

The same code path backs .github/workflows/member-from-issue.yml, so a person
who fills in the "Join EthioNLP" issue form gets an identical file via a pull
request without anyone running anything by hand.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    MEMBERS_DIR,
    get_json,
    info,
    slugify,
    step,
    warn,
)

KNOWN_FOCUS = {"data", "models", "applications", "evaluation", "capacity", "linguistics"}


def detect(url: str) -> tuple[str, str]:
    """Return (kind, handle-or-url) for a profile URL."""
    u = url.strip().rstrip("/")
    patterns = [
        ("github", r"github\.com/([^/?#]+)"),
        ("huggingface", r"huggingface\.co/([^/?#]+)"),
        ("orcid", r"orcid\.org/([\dX-]+)"),
        ("scholar", r"(scholar\.google\.[^/]+/citations\?.*)"),
        ("dblp", r"dblp\.org/pid/([^.]+)"),
        ("semantic_scholar", r"semanticscholar\.org/author/[^/]*/(\d+)"),
        ("linkedin", r"(linkedin\.com/in/[^/?#]+)"),
        ("twitter", r"(?:twitter|x)\.com/([^/?#]+)"),
    ]
    for kind, pattern in patterns:
        match = re.search(pattern, u, re.I)
        if match:
            return kind, match.group(1)
    return "website", u


def enrich_github(handle: str, profile: dict) -> None:
    data = get_json(f"https://api.github.com/users/{handle}")
    if not data:
        warn(f"github user {handle} not found")
        return
    profile.setdefault("name", data.get("name") or handle)
    if data.get("blog"):
        blog = data["blog"]
        profile.setdefault("website", blog if blog.startswith("http") else f"https://{blog}")
    if data.get("company"):
        profile.setdefault("affiliation", data["company"].lstrip("@"))
    if data.get("bio"):
        profile.setdefault("bio", data["bio"])
    if data.get("twitter_username"):
        profile.setdefault("twitter", data["twitter_username"])
    if data.get("avatar_url"):
        profile.setdefault("photo", data["avatar_url"])
    info(f"github: {data.get('name') or handle}")


def enrich_huggingface(handle: str, profile: dict) -> None:
    data = get_json(f"https://huggingface.co/api/users/{handle}/overview")
    if not data:
        # The overview endpoint is not public for every account; the handle is
        # still worth keeping, because sync_huggingface.py only needs that.
        info(f"huggingface: {handle} (profile not public, handle recorded)")
        return
    if data.get("fullname"):
        profile.setdefault("name", data["fullname"])
    if data.get("avatarUrl"):
        profile.setdefault("photo", data["avatarUrl"])
    info(f"huggingface: {data.get('fullname') or handle}")


def enrich_orcid(orcid: str, profile: dict) -> None:
    data = get_json(f"https://pub.orcid.org/v3.0/{orcid}/person")
    if not data:
        warn(f"orcid {orcid} not readable")
        return
    name = data.get("name") or {}
    given = ((name.get("given-names") or {}) or {}).get("value")
    family = ((name.get("family-name") or {}) or {}).get("value")
    if given and family:
        profile.setdefault("name", f"{given} {family}")

    urls = ((data.get("researcher-urls") or {}) or {}).get("researcher-url") or []
    for entry in urls:
        value = ((entry.get("url") or {}) or {}).get("value")
        if value and "http" in value:
            profile.setdefault("website", value)
            break
    info(f"orcid: {profile.get('name', orcid)}")


FIELD_ORDER = [
    # `title` duplicates `name` on purpose: Jekyll uses it for the page title and
    # would otherwise derive one from the filename slug.
    "name", "title", "role", "affiliation", "location", "photo", "order", "focus", "founder",
    "alumni", "website", "github", "huggingface", "scholar", "orcid",
    "semantic_scholar", "dblp", "linkedin", "twitter",
]


def render(profile: dict, bio: str) -> str:
    lines = ["---"]
    for key in FIELD_ORDER:
        value = profile.get(key)
        if value in (None, "", []):
            # Keep the identity keys visible-but-empty; they are the ones a
            # member is most likely to fill in later, and the sync scripts
            # look for exactly these names.
            if key in ("huggingface", "orcid", "semantic_scholar", "dblp", "scholar"):
                lines.append(f"{key}:")
            continue
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(value)}]")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif re.search(r"[:#]", str(value)):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    if bio:
        lines += ["", bio.strip()]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="*", help="profile URLs (github, huggingface, orcid, …)")
    parser.add_argument("--name", help="override the detected name")
    parser.add_argument("--role", help="e.g. 'PhD student'")
    parser.add_argument("--affiliation")
    parser.add_argument("--location")
    parser.add_argument("--focus", help="comma-separated: " + ", ".join(sorted(KNOWN_FOCUS)))
    parser.add_argument("--bio", default="", help="one short paragraph")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    parser.add_argument("--json", help="read all of the above from a JSON object instead")
    args = parser.parse_args()

    profile: dict = {}
    urls = list(args.urls)
    bio = args.bio

    if args.json:
        payload = json.loads(Path(args.json).read_text(encoding="utf-8"))
        urls += payload.pop("urls", [])
        bio = payload.pop("bio", bio) or ""
        profile.update({k: v for k, v in payload.items() if v})

    if not urls and not (args.name or profile.get("name")):
        parser.error("give at least one profile URL, or --name")

    step("Reading profiles")
    for url in urls:
        kind, handle = detect(url)
        if kind == "github":
            profile.setdefault("github", handle)
            enrich_github(handle, profile)
        elif kind == "huggingface":
            profile.setdefault("huggingface", handle)
            enrich_huggingface(handle, profile)
        elif kind == "orcid":
            profile.setdefault("orcid", handle)
            enrich_orcid(handle, profile)
        elif kind == "scholar":
            profile.setdefault("scholar", url.strip())
            info(f"scholar: recorded")
        elif kind == "dblp":
            profile.setdefault("dblp", handle)
            info(f"dblp: {handle}")
        elif kind == "semantic_scholar":
            profile.setdefault("semantic_scholar", handle)
            info(f"semantic scholar: {handle}")
        elif kind == "linkedin":
            profile.setdefault("linkedin", f"https://www.{handle}")
            info("linkedin: recorded")
        elif kind == "twitter":
            profile.setdefault("twitter", handle)
        else:
            profile.setdefault("website", url.strip())
            info(f"website: {url.strip()}")

    for key in ("name", "role", "affiliation", "location"):
        value = getattr(args, key, None)
        if value:
            profile[key] = value

    if args.focus:
        wanted = [f.strip() for f in args.focus.split(",") if f.strip()]
        unknown = [f for f in wanted if f not in KNOWN_FOCUS]
        if unknown:
            warn(f"unknown focus area(s) ignored: {', '.join(unknown)}")
        profile["focus"] = [f for f in wanted if f in KNOWN_FOCUS]

    bio = profile.pop("bio", "") or bio

    if not profile.get("name"):
        warn("could not determine a name, pass --name")
        return 1

    profile.setdefault("title", profile["name"])
    # Sorts after the curated roster and the Hugging Face import.
    profile.setdefault("order", 900)
    slug = slugify(profile["name"])
    path = MEMBERS_DIR / f"{slug}.md"
    if path.exists() and not args.force:
        warn(f"{path.relative_to(path.parents[1])} already exists (use --force to overwrite)")
        return 1

    MEMBERS_DIR.mkdir(exist_ok=True)
    path.write_text(render(profile, bio), encoding="utf-8")

    step("Done")
    info(f"wrote _members/{slug}.md")
    info("review it, then run `make sync` to pull in their models, repos and papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
