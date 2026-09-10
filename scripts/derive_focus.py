#!/usr/bin/env python3
"""Work out what each member actually works on, from what they have published.

A hand-entered `focus:` field in `_members/*.md` records an impression rather
than a finding: nothing checks it against the person's publications or
releases, and most member files leave it empty.

This derives it instead, from three kinds of evidence:

  publications  each carries `tracks` from classify_publications.py and
                `members` listing whose it is
  artifacts     models and datasets on Hugging Face carry a `focus` already,
                and `via_member` says whose account they came through
  repositories  GitHub repos, matched by owner

A track is kept for a person when it accounts for at least MIN_SHARE of their
evidence and has at least MIN_ITEMS behind it, so one stray keyword match does
not put someone in a field they have never worked in. The result is written to
the generated expertise file as `tracks`, ordered by weight.

This is the default, not the last word. A member who sets `focus:` in their
own file overrides it completely, which is how anyone corrects their entry. The
values that were there before came from a maintainer scaffolding the files, not
from the members, so they were cleared rather than treated as declarations.

    python3 scripts/derive_focus.py
    python3 scripts/derive_focus.py --check   # report, write nothing
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, info, step, warn  # noqa: E402

GENERATED = ROOT / "_data" / "generated"
MEMBERS = ROOT / "_members"

MIN_SHARE = 0.15   # of a person's evidence, before a track is claimed for them
MIN_ITEMS = 2      # and at least this many items, so one paper is not a field
# No cap on what is stored: someone who genuinely works across five areas
# should have five recorded. The card shows the top three and the profile
# page shows them all, so the trimming is a display decision, not a claim
# about the person.


def load(name: str) -> dict:
    path = GENERATED / name
    if not path.exists():
        warn(f"{name} not found; run the sync first")
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def curated_focus() -> dict[str, list[str]]:
    """Whatever a member file already declares, used only as a fallback."""
    out = {}
    for path in sorted(MEMBERS.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^focus:\s*\[(.*?)\]\s*$", text, re.M)
        if not m:
            continue
        vals = [v.strip().strip("'\"") for v in m.group(1).split(",") if v.strip()]
        if vals:
            out[path.stem] = vals
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    args = parser.parse_args()

    pubs = (load("publications.yml") or {}).get("publications") or []
    hf = (load("huggingface.yml") or {}).get("artifacts") or []
    gh = (load("github.yml") or {}).get("repos") or []
    expertise = load("expertise.yml")
    if not expertise:
        return 1

    if not any(p.get("tracks") for p in pubs):
        warn("no publication has tracks; run classify_publications.py first")

    weights: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)

    for rec in pubs:
        for slug in rec.get("members") or []:
            for track in rec.get("tracks") or []:
                weights[slug][track] += 1

    # An artifact is a stronger signal than a paper: releasing a dataset is
    # more direct evidence of working on datasets than writing about one.
    for art in hf:
        slug = art.get("via_member")
        focus = art.get("focus")
        if slug and focus:
            weights[slug][focus] += 2

    for repo in gh:
        slug = repo.get("via_member") or repo.get("member")
        focus = repo.get("focus")
        if slug and focus:
            weights[slug][focus] += 2

    curated = curated_focus()
    step("Deriving focus areas")
    derived, kept, thin = {}, 0, 0
    for slug, counter in sorted(weights.items()):
        total = sum(counter.values())
        picks = [t for t, n in counter.most_common()
                 if n >= MIN_ITEMS and n / total >= MIN_SHARE]
        if not picks:
            thin += 1
            continue
        derived[slug] = picks
        if slug in curated:
            kept += 1

    for entry in expertise.get("per_member") or []:
        entry["tracks"] = derived.get(entry["slug"], [])

    expertise["focus_method"] = (
        "Focus areas are counted from each person's own publications, models, "
        "datasets and repositories, not declared. A track is shown when it is "
        f"at least {int(MIN_SHARE * 100)}% of what was found for them and rests "
        f"on at least {MIN_ITEMS} items. A member who sets their own focus "
        "field overrides this entirely."
    )

    info(f"{len(derived)} people given a focus from their own work")
    info(f"{thin} had too little evidence to call")
    info(f"{kept} of those had a hand-typed value, now superseded")
    for slug, picks in list(derived.items())[:8]:
        info(f"  {slug:28} {', '.join(picks)}  (was: {curated.get(slug) or 'none'})")

    if args.check:
        info("--check: nothing written")
        return 0

    (GENERATED / "expertise.yml").write_text(
        yaml.safe_dump(expertise, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    info("wrote tracks into _data/generated/expertise.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
