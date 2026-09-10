#!/usr/bin/env python3
"""Turn team-registration form responses into a proposed entry.

GitHub Pages serves static files and runs no code, so a form on this site
cannot post to this site. The way round it is to let a form tool hold the
responses and have a scheduled job here read them back: the form is somebody
else's server, the sheet is the queue, and this script drains the queue into a
pull request.

    Google Form  ->  responses sheet  ->  published as CSV
                                             |
                       daily GitHub Action ---+
                                             |
                       this script -> _data/organisations.yml -> pull request

The person registering needs no GitHub account and no login of any kind. A
maintainer still reviews every entry, which matters more here than for news:
registering a team makes its output count as EthioNLP's own, so it should not
be self-service.

Set `TEAM_FORM_CSV` to the published-CSV URL of the responses sheet, and
`team_form_url` in `_config.yml` to the public form URL, which is what turns
the button on. With the variable unset this exits quietly, so it is safe to
merge before anything is configured.

    python3 scripts/from_team_form.py            # append pending entries
    python3 scripts/from_team_form.py --dry-run  # print what it would add
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

from lib.common import ROOT, get_text, info, step, warn  # noqa: E402

TEAMS_FILE = ROOT / "_data" / "organisations.yml"
SEEN_FILE = ROOT / "_data" / "generated" / "team_seen.json"

# Heading matching is deliberately loose, because people rename form questions
# and a registration that fails because a column is called "Team name" rather
# than "name" is a registration lost.
#
# Order matters and is not alphabetical: each column is claimed by the first
# field that matches it and is then out of the running. "Describe the team" and
# "What kind?" both contain a word the summary would otherwise take, so the
# narrow fields are matched first and the catch-all last.
FIELDS = [
    ("huggingface", ("hugging", "hf")),
    ("github", ("github",)),
    ("website", ("website", "homepage", "url", "site")),
    ("kind", ("kind", "type")),
    ("lead", ("lead", "contact person", "who leads")),
    ("name", ("team", "group", "lab", "organisation name", "name")),
    ("summary", ("summary", "describe", "description", "about", "what the")),
]

KINDS = {"lab", "project", "community", "company"}


def read_row(row: dict) -> dict:
    """Map a response row onto our fields, one column to at most one field."""
    out = {f: "" for f, _ in FIELDS}
    taken: set[str] = set()
    for field, words in FIELDS:
        for heading, value in row.items():
            low = (heading or "").strip().lower()
            if heading in taken or not (value or "").strip():
                continue
            if any(w in low for w in words):
                out[field] = value.strip()
                taken.add(heading)
                break
    return out


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def handle(value: str) -> str:
    """Accept a full URL or a bare handle; store the handle."""
    if not value:
        return ""
    value = value.strip().rstrip("/")
    return value.split("/")[-1] if "/" in value else value


def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except Exception:
        warn(f"{SEEN_FILE.name} unreadable, treating every response as new")
        return set()


def read_form(seen: set[str], existing: set[str]) -> list[dict]:
    url = os.environ.get("TEAM_FORM_CSV")
    if not url:
        info("TEAM_FORM_CSV is not set, nothing to read")
        return []

    step("Team registration form")
    raw = get_text(url)
    if not raw:
        warn("could not read TEAM_FORM_CSV")
        return []

    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    rows = list(csv.DictReader(io.StringIO(text)))
    info(f"{len(rows)} response(s) in the sheet")

    out = []
    for row in rows:
        fields = read_row(row)
        name = fields["name"]
        if not name:
            continue

        slug = slugify(name)
        # The whole row is the identity, so an edited response counts as new
        # and a maintainer sees the correction rather than the original.
        key = "team:" + re.sub(r"\s+", " ", "|".join(
            f"{k}={v}" for k, v in sorted(row.items())))[:400]
        if key in seen:
            continue
        if slug in existing:
            info(f"{name} is already registered, skipping")
            seen.add(key)
            continue

        kind = fields["kind"].lower()
        out.append({
            "key": key,
            "name": name,
            "slug": slug,
            "huggingface": handle(fields["huggingface"]),
            "github": handle(fields["github"]),
            "website": fields["website"],
            "kind": kind if kind in KINDS else "lab",
            "summary": " ".join(fields["summary"].split()),
            "lead": fields["lead"],
        })
    info(f"{len(out)} new")
    return out


def existing_slugs() -> set[str]:
    """Read the slugs already registered, without needing a YAML parser."""
    if not TEAMS_FILE.exists():
        return set()
    return set(re.findall(r"^\s*slug:\s*(\S+)\s*$",
                          TEAMS_FILE.read_text(encoding="utf-8"), re.M))


def render(team: dict, today: str) -> str:
    """One entry, commented out, with the reviewer's checklist above it.

    Commented out on purpose. An automatically appended entry would put a
    team's models into the site's own totals the moment the job ran; a
    maintainer uncommenting three lines is the review step, and it is the
    smallest possible one.
    """
    lines = [
        "",
        f"  # Submitted through the form on {today}. Check the two handles are",
        "  # the organisations and not a personal account, then uncomment.",
        f"  # - name: {team['name']}",
        f"  #   slug: {team['slug']}",
    ]
    for key in ("huggingface", "github", "website", "lead"):
        if team[key]:
            lines.append(f"  #   {key}: {team[key]}")
    lines.append(f"  #   kind: {team['kind']}")
    lines.append(f"  #   joined: {today[:7]}")
    if team["summary"]:
        lines.append(f"  #   summary: {team['summary']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", default="", help="date stamp, for reproducible runs")
    args = parser.parse_args()

    today = args.today or os.environ.get("TODAY") or ""
    if not today:
        from datetime import date, timezone, datetime
        today = datetime.now(timezone.utc).date().isoformat()

    seen = load_seen()
    teams = read_form(seen, existing_slugs())
    if not teams:
        info("nothing to add")
        return 0

    step("Writing")
    body = "".join(render(t, today) for t in teams)
    for t in teams:
        info(f"{t['name']}  ({t['huggingface'] or 'no HF'} / {t['github'] or 'no GitHub'})")
        seen.add(t["key"])

    if args.dry_run:
        print(body)
        info("--dry-run: nothing written")
        return 0

    with TEAMS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(body)
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")
    info(f"appended to {TEAMS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
