#!/usr/bin/env python3
"""Import the Hugging Face organisation's members into `_members/`.

Membership of the EthioNLP organisation on the Hub is granted by an admin, so
it is a real signal of belonging, and it carries the one identifier the
ecosystem sync most needs. This script:

1. matches each Hub member against the existing `_members/*.md` files, by
   handle first and then by name, and fills in their `huggingface:` key;
2. creates a file for anyone not already listed, placed after the curated
   roster in display order.

It never overwrites a value a human has written, and re-running it is safe: a
second run reports "already listed" for everyone and changes nothing.

    python3 scripts/import_hf_members.py            # apply
    python3 scripts/import_hf_members.py --check    # report only

Ordering
────────
`order:` drives the sequence on the community page. The curated roster keeps the
order it had on the previous site; imported members follow, and anyone added
later through the join form lands at the end.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    MEMBERS_DIR,
    get_json,
    info,
    norm_name,
    read_members,
    slugify,
    step,
    warn,
)

ORG = "EthioNLP"
API = f"https://huggingface.co/api/organizations/{ORG}/members"

# Where imported members start. The curated roster occupies 1..N.
IMPORT_ORDER_BASE = 100

# Hub avatars are either an uploaded image or a generated identicon. The
# identicons are worse than nothing, a wall of pastel noise, so only real
# uploads are kept and everyone else falls back to their initials.
REAL_AVATAR = "cdn-avatars.huggingface.co"

# Hub display names are often partial ("Moges Ahmed" for Moges Ahmed Mehamed,
# "Yonas" for Yonas Chanie). Matching on the exact string alone would create a
# second, emptier profile for someone already listed, so `same_person` below
# also accepts one name being contained in the other.
#
# This map is for the remaining cases the rule cannot reach: a Hub name that is
# not a substring of the person's real name at all.
KNOWN_NAMES = {
    "walelign": "Walelign Tewabe Sewunetie",
    "sewunetie": "Walelign Tewabe Sewunetie",
}


def same_person(hub_name: str, member: dict) -> bool:
    """Whether a Hub display name refers to an already-listed member.

    Accepts a partial name when its tokens are a subset of the member's, which
    is the common case, and requires two shared tokens so that a shared surname
    alone is never enough. A single-token Hub name is handled by the caller,
    which only accepts it when exactly one member matches.
    """
    hub = set(norm_name(hub_name).split())
    if len(hub) < 2:
        return False

    candidates = [member.get("name") or ""] + list(member.get("aliases") or [])
    for candidate in candidates:
        tokens = set(norm_name(candidate).split())
        shared = hub & tokens
        if len(shared) >= 2 and (hub <= tokens or tokens <= hub):
            return True
    return False


def single_token_match(hub_name: str, members: list[dict]) -> dict | None:
    """Resolve a one-word Hub name, but only when it is unambiguous."""
    token = norm_name(hub_name)
    if not token or " " in token:
        return None
    hits = [
        m for m in members
        if token in norm_name(m.get("name")).split()
        or any(token in norm_name(a).split() for a in m.get("aliases") or [])
    ]
    return hits[0] if len(hits) == 1 else None


def patch_front_matter(path: Path, key: str, value: str) -> bool:
    """Set a front-matter key if it is absent or empty. Returns True if changed."""
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^{key}:[^\S\n]*\S", text, re.M):
        return False

    empty = re.compile(rf"^{key}:[^\S\n]*$", re.M)
    if empty.search(text):
        text = empty.sub(f"{key}: {value}", text, count=1)
    else:
        parts = text.split("---", 2)
        if len(parts) < 3:
            warn(f"{path.name}: unexpected front matter, skipping")
            return False
        parts[1] = parts[1].rstrip("\n") + f"\n{key}: {value}\n"
        text = "---".join(parts)

    path.write_text(text, encoding="utf-8")
    return True


def render(name: str, handle: str, avatar: str | None, order: int) -> str:
    lines = [
        "---",
        f"name: {name}",
        f"title: {name}",
        "role:",
        "affiliation:",
    ]
    if avatar:
        lines.append(f'photo: "{avatar}"')
    lines += [
        f"order: {order}",
        "focus: []",
        "website:",
        "github:",
        f"huggingface: {handle}",
        "scholar:",
        "orcid:",
        "semantic_scholar:",
        "dblp:",
        "# Imported from the EthioNLP Hugging Face organisation. Fill in the",
        "# blanks above. A role, an affiliation and any one scholarly",
        "# identifier is enough for this profile to fill itself in from then on.",
        "---",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report only")
    args = parser.parse_args()

    hub = get_json(API)
    if not hub:
        warn(f"could not read the member list for {ORG}")
        return 1

    members = read_members()
    by_handle = {
        (m.get("huggingface") or "").strip().lower(): m for m in members if m.get("huggingface")
    }
    by_name = {norm_name(m.get("name")): m for m in members}
    for m in members:
        for alias in m.get("aliases") or []:
            by_name.setdefault(norm_name(alias), m)

    highest = max((m.get("order") or 0) for m in members) if members else 0
    next_order = max(highest + 1, IMPORT_ORDER_BASE)

    linked = created = skipped = 0

    step(f"{len(hub)} members in the {ORG} organisation")
    for entry in hub:
        handle = (entry.get("user") or "").strip()
        name = (entry.get("fullname") or "").strip() or handle
        if not handle:
            continue

        name = KNOWN_NAMES.get(norm_name(name), name)
        name = KNOWN_NAMES.get(handle.lower(), name)

        existing = by_handle.get(handle.lower()) or by_name.get(norm_name(name))
        if not existing:
            existing = next((m for m in members if same_person(name, m)), None)
        if not existing:
            existing = single_token_match(name, members)

        if existing:
            if existing.get("huggingface"):
                skipped += 1
                continue
            info(f"{name:<30} → linked to _members/{existing['slug']}.md")
            linked += 1
            if not args.check:
                patch_front_matter(existing["_path"], "huggingface", handle)
            continue

        slug = slugify(name)
        path = MEMBERS_DIR / f"{slug}.md"
        if path.exists():
            skipped += 1
            continue

        avatar = entry.get("avatarUrl") or ""
        avatar = avatar if REAL_AVATAR in avatar else None

        info(f"{name:<30} → new _members/{slug}.md")
        created += 1
        if not args.check:
            path.write_text(render(name, handle, avatar, next_order), encoding="utf-8")
        next_order += 1

    step("Summary")
    info(f"{linked} linked to existing profiles, {created} created, {skipped} already complete")
    if created:
        info("new profiles have no role or affiliation, those are worth filling in by hand")
    if args.check:
        info("run without --check to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
