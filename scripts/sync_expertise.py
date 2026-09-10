#!/usr/bin/env python3
"""Derive who works on which language, and write _data/generated/expertise.yml.

Nobody declares this. It is read off what people have actually published:

* Hugging Face artifacts carry explicit language tags, which are taken as given;
* publications and repositories do not, so the language is inferred by looking
  for language names in the title, abstract, description and topics.

The inference is deliberately narrow. It matches a language's own name and the
handful of spellings that name is really written with, "Afaan Oromo", "Oromo",
"Oromiffa", as whole words, and nothing else. It does not guess from an
author's affiliation, and it does not treat "Ethiopian" as a language. A missing
mapping is a much smaller problem than a wrong one: this page tells a student
who to write to, and sending them to someone who has never touched the language
wastes both their time.

Usage:
    python3 scripts/sync_expertise.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    ETHIOPIAN_LANGUAGES,
    GENERATED,
    info,
    read_members,
    step,
    touch_meta,
    warn,
    write_generated,
)

# Spellings each language is written with in paper titles and repository names.
# Only forms that unambiguously mean that language belong here, "Tigray" is a
# region and "Gurage" is a cluster of them, so neither is listed.
ALIASES = {
    "Amharic": ["amharic", "amaric", "amharic-english"],
    "Tigrinya": ["tigrinya", "tigrigna", "tigriña"],
    "Afaan Oromo": ["afaan oromo", "afan oromo", "oromo", "oromiffa", "oromifa"],
    "Somali": ["somali"],
    "Afar": ["afar language", "afaraf"],
    "Sidama": ["sidama", "sidaama", "sidamo"],
    "Wolaytta": ["wolaytta", "wolaita", "wolayta", "welayta"],
    "Ge'ez": ["ge'ez", "geez", "ge ez", "ethiopic"],
    "Harari": ["harari"],
    "Awngi": ["awngi", "awagni", "agaw"],
    "Kafa": ["kafa noono", "kafi noono"],
    "Hadiyya": ["hadiyya", "hadiya"],
    "Nuer": ["nuer"],
    "Anuak": ["anuak", "anywa"],
    "Tigre": ["tigre language"],
    "Blin": ["blin", "bilen"],
    "Xamtanga": ["xamtanga", "khimtanga"],
    "Sebat Bet Gurage": ["sebat bet gurage", "chaha", "kistane"],
    "Bench": ["bench language"],
    "Gedeo": ["gedeo"],
    "Mursi": ["mursi"],
    "Kachama-Ganjule": ["kachama", "ganjule"],
}

# Glottolog, which the language catalogue follows, spells several of these
# differently from the Hugging Face tag vocabulary we use elsewhere. Emitting
# both names lets the catalogue join on its own spelling without either source
# having to change.
CATALOGUE_NAMES = {
    "Afaan Oromo": "Oromo",
    "Sidama": "Sidamo",
    "Ge'ez": "Geez",
    "Sebat Bet Gurage": "Sebat Bet Gurage",
}


# Compiled once. Word boundaries matter: without them "oromo" matches inside
# "Oromoo" harmlessly but "afar" matches inside "afar-reaching", and "bench"
# inside "benchmark", which is why those two only have specific forms above.
PATTERNS = {
    name: re.compile(r"\b(" + "|".join(re.escape(a) for a in aliases) + r")\b", re.I)
    for name, aliases in ALIASES.items()
}


def detect(*fields) -> list[str]:
    """Languages named in any of the given text fields."""
    parts = []
    for field in fields:
        if isinstance(field, (list, tuple)):
            parts.extend(str(f) for f in field if f)
        elif field:
            parts.append(str(field))
    blob = " ".join(parts)
    if not blob:
        return []
    return [name for name, pattern in PATTERNS.items() if pattern.search(blob)]


def load(name: str) -> dict:
    path = GENERATED / name
    if not path.exists():
        warn(f"{name} not found, run the other sync scripts first")
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = parser.parse_args()

    # Only people who have confirmed their listing. This mapping is published
    # as "who to write to", and it must not send anyone to someone who has not
    # agreed to be on the site.
    members = [m for m in read_members() if m.get("confirmed") is not False]
    by_slug = {m["slug"]: m for m in members}

    hf = load("huggingface.yml")
    pubs = load("publications.yml")
    repos = load("github.yml")

    # slug → language → {artifacts, papers, repos}
    tally: dict[str, dict[str, dict]] = {}

    def credit(slug: str, language: str, bucket: str) -> None:
        if slug not in by_slug:
            return
        langs = tally.setdefault(slug, {})
        counts = langs.setdefault(language, {"artifacts": 0, "papers": 0, "repos": 0})
        counts[bucket] += 1

    step("Hugging Face artifacts")
    n = 0
    for artifact in hf.get("artifacts") or []:
        # Broad multilingual work is not evidence that someone works on any one
        # of its hundred languages, so it does not count towards expertise.
        if artifact.get("breadth") != "focused":
            continue
        # Only this community's own work counts towards expertise; an artifact
        # from an organisation a member merely belongs to does not.
        if artifact.get("tier") not in ("ethionlp", "member"):
            continue
        slug = artifact.get("member")
        if not slug:
            continue
        for language in artifact.get("languages") or []:
            credit(slug, language, "artifacts")
            n += 1
    info(f"{n} member-language credits")

    step("Publications")
    n = 0
    for pub in pubs.get("publications") or []:
        languages = detect(pub.get("title"), pub.get("abstract"))
        if not languages:
            continue
        for slug in pub.get("members") or []:
            for language in languages:
                credit(slug, language, "papers")
                n += 1
    info(f"{n} member-language credits")

    step("Repositories")
    n = 0
    for repo in repos.get("repos") or []:
        slug = repo.get("member")
        if not slug:
            continue
        for language in detect(repo.get("name"), repo.get("description"), repo.get("topics")):
            credit(slug, language, "repos")
            n += 1
    info(f"{n} member-language credits")

    # ── Shape the output ─────────────────────────────────────────────────────
    per_member = []
    for slug, languages in tally.items():
        rows = []
        for name, counts in languages.items():
            total = counts["artifacts"] + counts["papers"] + counts["repos"]
            rows.append({"name": name, "total": total, **counts})
        rows.sort(key=lambda r: (-r["total"], r["name"]))
        per_member.append({
            "slug": slug,
            "name": by_slug[slug]["name"],
            "languages": rows,
            "top": rows[0]["name"] if rows else None,
        })
    per_member.sort(key=lambda m: (-sum(r["total"] for r in m["languages"]), m["name"]))

    per_language: dict[str, list] = {}
    for entry in per_member:
        for row in entry["languages"]:
            per_language.setdefault(row["name"], []).append({
                "slug": entry["slug"],
                "name": entry["name"],
                "total": row["total"],
                "artifacts": row["artifacts"],
                "papers": row["papers"],
                "repos": row["repos"],
            })

    languages_out = []
    for name, people in per_language.items():
        people.sort(key=lambda p: (-p["total"], p["name"]))
        iso = next((c for c, n_ in ETHIOPIAN_LANGUAGES.items() if n_ == name and len(c) == 3), None)
        languages_out.append({
            "name": name,
            "catalogue_name": CATALOGUE_NAMES.get(name, name),
            "iso": iso,
            "people": people,
            "count": len(people),
        })
    languages_out.sort(key=lambda l: (-l["count"], l["name"]))

    payload = {
        "totals": {
            "members": len(per_member),
            "languages": len(languages_out),
            "unmapped": len(members) - len(per_member),
        },
        "method": (
            "Hugging Face language tags are taken as given. For publications and "
            "repositories the language is inferred by matching its name, and the "
            "spellings that name is actually written with, as whole words in the "
            "title, abstract, description and topics. Broad multilingual work is "
            "excluded: contributing to a hundred-language model is not evidence "
            "of working on any one of those languages. Absence here means nothing "
            "was detected, not that the person does not work on the language."
        ),
        "per_member": per_member,
        "per_language": languages_out,
    }

    step("Summary")
    info(f"{len(per_member)} of {len(members)} members mapped, "
         f"across {len(languages_out)} languages")
    for entry in languages_out[:8]:
        names = ", ".join(p["name"] for p in entry["people"][:3])
        more = f" +{entry['count'] - 3}" if entry["count"] > 3 else ""
        info(f"{entry['name']:<18} {entry['count']:>2} people   {names}{more}")

    if args.dry_run:
        info("--dry-run: nothing written")
        return 0

    write_generated("expertise.yml", payload, "sync_expertise.py")
    touch_meta("expertise")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
