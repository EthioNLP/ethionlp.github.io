#!/usr/bin/env python3
"""Two halves of the member-driven publication flow.

    --preview   resolve the links in an issue and print a Markdown summary
                for the bot to post back. Writes nothing.
    --apply     append the resolved records to _data/publications_manual.yml.

The split is the point: a member sees the exact author list, venue and year
before anything is written, and approval is a separate, deliberate step. The
monthly sync then treats these as curated, so they win over whatever an
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


def existing_records() -> list[dict]:
    rows = []
    for path, key in ((CURATED, None), (DATA / "generated" / "publications.yml", "publications")):
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        rows += (data.get(key) if key else data) or []
    return rows


def find_existing(rec: dict, rows: list[dict]) -> dict | None:
    """The record this one is about, matched on an identifier then the title.

    Identifier first: a paper the aggregator titled differently is still the
    same paper, and treating it as new is how a duplicate gets created.
    """
    doi = (rec.get("doi") or "").lower()
    arxiv = (rec.get("arxiv") or "").strip()
    anth = (rec.get("anthology") or "").strip()
    for r in rows:
        if doi and (r.get("doi") or "").lower() == doi:
            return r
        if arxiv and (r.get("arxiv") or "").strip() == arxiv:
            return r
        if anth and (r.get("anthology") or "").strip() == anth:
            return r
    key = norm_title(rec.get("title") or "")
    for r in rows:
        if r.get("title") and norm_title(r["title"]) == key:
            return r
    return None


def author_diff(old: dict, new: dict) -> list[str]:
    """What approving this would change about the author list."""
    a = [x.get("name") for x in (old.get("authors") or [])]
    b = [x.get("name") for x in (new.get("authors") or [])]
    out = []
    if len(a) != len(b):
        out.append(f"author count {len(a)} -> {len(b)}")
    missing = [n for n in b if n not in a]
    extra = [n for n in a if n not in b]
    if missing:
        out.append("adds: " + ", ".join(missing))
    if extra:
        out.append("removes: " + ", ".join(extra))
    moved = sum(1 for x, y in zip(a, b) if x != y)
    if moved and not missing and not extra:
        out.append(f"{moved} author(s) reordered")
    return out


def gather(body: str) -> tuple[list[dict], list[dict], list[dict]]:
    """(new records, corrections to existing records, problems)."""
    rows = existing_records()
    new, corrections, problems = [], [], []
    for raw in links_from(body):
        rec = resolve(raw)
        if not rec or not rec.get("title"):
            problems.append({"link": raw, "why": "could not be resolved"})
            continue
        live = find_existing(rec, rows)
        if live is None:
            new.append(rec)
            rows.append(rec)
            continue
        changes = author_diff(live, rec)
        if live.get("title") != rec.get("title"):
            changes.insert(0, f"title -> {rec['title']}")
        if not changes:
            problems.append({"link": raw, "why": f"already listed and identical: {rec['title']}"})
            continue
        rec["_replaces"] = live.get("title")
        rec["_changes"] = changes
        corrections.append(rec)
    return new, corrections, problems


def preview(records: list[dict], corrections: list[dict],
            problems: list[dict], member: str | None) -> str:
    known = {m["slug"] for m in read_members()}
    lines = []
    if member and member not in known:
        lines += [f"> No member file matches `{member}`. The papers will still be "
                  "added; the link to your profile will not.", ""]
    def block(i, r):
        authors = ", ".join(a["name"] for a in r.get("authors") or [])
        return [
            f"**{i}. {r['title']}**",
            "",
            f"- Authors ({len(r.get('authors') or [])}): {authors or '_none found_'}",
            f"- Venue: {r.get('venue') or '_unknown_'} ({r.get('year') or '?'})",
            f"- Source of record: {r['source_of_record']}",
            f"- DOI: `{r.get('doi') or '—'}`",
            "",
        ]

    if records:
        lines += [f"### {len(records)} new paper(s)", ""]
        for i, r in enumerate(records, 1):
            lines += block(i, r)

    if corrections:
        lines += [f"### {len(corrections)} correction(s) to papers already listed", ""]
        for i, r in enumerate(corrections, 1):
            lines += block(i, r)
            lines.append(f"  Replaces the record currently titled "
                         f"*{r['_replaces']}*. Approving would:")
            lines += [f"  - {c}" for c in r["_changes"]]
            lines.append("")

    if not records and not corrections:
        lines += ["Nothing to add or correct from this issue.", ""]
    else:
        lines.insert(0, "")
        lines.insert(0, "Check the author lists below, then add the **approved** "
                        "label to publish them.")
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
        note = ("Corrects the record previously titled "
                f"{r['_replaces']!r}." if r.get("_replaces") else "")
        block = yaml.safe_dump([entry], allow_unicode=True, sort_keys=False, width=100)
        chunks.append(f"# From a member submission, metadata from "
                      f"{r['source_of_record']}.\n"
                      + (f"# {note}\n" if note else "") + block)
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
    records, corrections, problems = gather(body)

    if args.preview:
        print(preview(records, corrections, problems, args.member.strip() or None))
        return 0
    n = apply(records + corrections, args.member.strip() or None)
    print(f"{n} publication(s) added to {CURATED.relative_to(CURATED.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
