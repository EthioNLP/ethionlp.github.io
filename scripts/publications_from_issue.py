#!/usr/bin/env python3
"""Two halves of the member-driven publication flow.

    --preview   resolve the links in an issue and print a Markdown summary
                for the bot to post back. Writes nothing.
    --apply     append the resolved records to _data/publications_manual.yml.

The split is the point: a member sees the exact author list, venue and year
before anything is written, and approval is a separate, deliberate step. The
nightly sync then treats these as curated, so they win over whatever an
aggregator later decides the same paper is called.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from fetch_publication import resolve  # noqa: E402
from lib.common import DATA, norm_title, read_members  # noqa: E402

CURATED = DATA / "publications_manual.yml"


def links_from(body: str) -> list[str]:
    """The lines under the "Links to your papers" heading."""
    out, grabbing = [], False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("###"):
            grabbing = "link" in s.lower()
            continue
        if grabbing and s and not s.startswith("- ["):
            out.append(s)
    # Fall back to any identifier-looking line, so a free-form issue still works.
    if not out:
        for line in body.splitlines():
            s = line.strip()
            if "aclanthology.org" in s or "arxiv.org" in s or s.startswith("10."):
                out.append(s)
    return out


def existing_titles() -> set[str]:
    seen = set()
    for path, key in ((CURATED, None), (DATA / "generated" / "publications.yml", "publications")):
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        rows = data.get(key) if key else data
        for r in rows or []:
            if r.get("title"):
                seen.add(norm_title(r["title"]))
    return seen


def gather(body: str) -> tuple[list[dict], list[dict]]:
    """(records to add, problems to report)."""
    seen = existing_titles()
    records, problems = [], []
    for raw in links_from(body):
        rec = resolve(raw)
        if not rec or not rec.get("title"):
            problems.append({"link": raw, "why": "could not be resolved"})
            continue
        if norm_title(rec["title"]) in seen:
            problems.append({"link": raw, "why": f"already listed: {rec['title']}"})
            continue
        seen.add(norm_title(rec["title"]))
        records.append(rec)
    return records, problems


def preview(records: list[dict], problems: list[dict], member: str | None) -> str:
    known = {m["slug"] for m in read_members()}
    lines = []
    if member and member not in known:
        lines += [f"> No member file matches `{member}`. The papers will still be "
                  "added; the link to your profile will not.", ""]
    if records:
        lines.append(f"Found **{len(records)}** paper(s). Check the author lists, "
                     "then add the **approved** label to publish them.")
        lines.append("")
        for i, r in enumerate(records, 1):
            authors = ", ".join(a["name"] for a in r.get("authors") or [])
            lines += [
                f"**{i}. {r['title']}**",
                "",
                f"- Authors: {authors or '_none found_'}",
                f"- Venue: {r.get('venue') or '_unknown_'} ({r.get('year') or '?'})",
                f"- Source of record: {r['source_of_record']}",
                f"- DOI: `{r.get('doi') or '—'}`",
                "",
            ]
    else:
        lines.append("No new papers were resolved from this issue.")
        lines.append("")
    if problems:
        lines.append("Not added:")
        lines.append("")
        lines += [f"- `{p['link']}` — {p['why']}" for p in problems]
        lines.append("")
    lines.append("If an author name is wrong here, say so and it will be corrected "
                 "by hand rather than published.")
    return "\n".join(lines)


def apply(records: list[dict], member: str | None) -> int:
    if not records:
        return 0
    text = CURATED.read_text(encoding="utf-8") if CURATED.exists() else ""
    chunks = []
    for r in records:
        entry = {k: v for k, v in r.items()
                 if k in ("title", "authors", "year", "venue", "doi", "arxiv",
                          "anthology", "url") and v}
        block = yaml.safe_dump([entry], allow_unicode=True, sort_keys=False, width=100)
        chunks.append(f"# Added from a member submission; "
                      f"metadata from {r['source_of_record']}.\n{block}")
    CURATED.write_text(text.rstrip("\n") + "\n\n" + "\n".join(chunks), encoding="utf-8")
    return len(records)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--member", default="")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8")
    records, problems = gather(body)

    if args.preview:
        print(preview(records, problems, args.member.strip() or None))
        return 0
    n = apply(records, args.member.strip() or None)
    print(f"{n} publication(s) added to {CURATED.relative_to(CURATED.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
